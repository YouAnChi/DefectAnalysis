package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/xuri/excelize/v2"
)

// 任务状态常量
const (
	StatusPending    = "pending"
	StatusProcessing = "processing"
	StatusCompleted  = "completed"
	StatusFailed     = "failed"
)

// 任务信息结构体
type Task struct {
	ID            string    `json:"id"`
	Status        string    `json:"status"`
	Total         int       `json:"total"`
	Processed     int       `json:"processed"`
	InputFile     string    `json:"input_file"`
	OutputFile    string    `json:"output_file"`
	KnowledgeFile string    `json:"knowledge_file"`
	Threshold     float64   `json:"threshold"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
	Error         string    `json:"error,omitempty"`
}

// 分析结果结构体
type AnalysisResult struct {
	Title         string `json:"title,omitempty"`
	Description   string `json:"description"`
	ScoreCategory string `json:"score_category,omitempty"`
	Analysis      string `json:"analysis"`
	Reasoning     string `json:"reasoning"`
	Error         string `json:"error,omitempty"`
}

// 任务结果响应结构体
type TaskResultsResponse struct {
	TaskID  string           `json:"task_id"`
	Status  string           `json:"status"`
	Results []AnalysisResult `json:"results"`
}

// 内存中存储任务信息
var (
	tasks      = make(map[string]*Task)
	tasksMutex = &sync.RWMutex{}
	tempDir    = "./temp"
)

func main() {
	// 创建临时目录
	if err := os.MkdirAll(tempDir, 0755); err != nil {
		log.Fatalf("无法创建临时目录: %v", err)
	}

	// 初始化Gin路由
	r := gin.Default()

	// 配置CORS
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST"},
		AllowHeaders:     []string{"Origin", "Content-Type"},
		ExposeHeaders:    []string{"Content-Length", "Content-Disposition"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// 提供静态文件服务
	r.Static("/css", "../frontend/css")
	r.Static("/js", "../frontend/js")
	r.StaticFile("/", "../frontend/index.html")
	r.StaticFile("/favicon.ico", "../frontend/favicon.ico")

	// API路由组
	api := r.Group("/api")
	{
		// 提交分析任务
		api.POST("/analyze", handleAnalyzeRequest)

		// 获取任务状态
		api.GET("/task/:id", getTaskStatus)

		// 获取分析结果
		api.GET("/results/:id", getTaskResults)

		// 下载分析结果
		api.GET("/download/:id", downloadResults)
	}

	// 启动服务器
	port := 8080
	log.Printf("服务器启动在 http://localhost:%d", port)
	if err := r.Run(fmt.Sprintf(":%d", port)); err != nil {
		log.Fatalf("启动服务器失败: %v", err)
	}
}

// 处理分析请求
func handleAnalyzeRequest(c *gin.Context) {
	// 创建新任务ID
	taskID := uuid.New().String()

	// 获取上传的Excel文件
	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请上传Excel文件"})
		return
	}

	// 保存Excel文件到临时目录
	inputFilePath := filepath.Join(tempDir, taskID+"_input.xlsx")
	if err := c.SaveUploadedFile(file, inputFilePath); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "保存文件失败"})
		return
	}

	// 设置输出文件路径
	outputFilePath := filepath.Join(tempDir, taskID+"_output.xlsx")

	// 获取知识库文件
	knowledgeFilePath := "defects_knowledge_base.json" // 默认知识库
	knowledgeFile, err := c.FormFile("knowledge_base")
	if err == nil {
		// 用户上传了自定义知识库
		knowledgeFilePath = filepath.Join(tempDir, taskID+"_knowledge.json")
		if err := c.SaveUploadedFile(knowledgeFile, knowledgeFilePath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "保存知识库文件失败"})
			return
		}
	} else {
		// 使用指定的知识库名称
		if knowledgeName := c.PostForm("knowledge_base_name"); knowledgeName != "" {
			knowledgeFilePath = knowledgeName
		}
	}

	// 获取相似度阈值
	threshold := 0.3 // 默认值
	if thresholdStr := c.PostForm("threshold"); thresholdStr != "" {
		if t, err := strconv.ParseFloat(thresholdStr, 64); err == nil && t >= 0 && t <= 1 {
			threshold = t
		}
	}

	// 创建任务记录
	task := &Task{
		ID:            taskID,
		Status:        StatusPending,
		Total:         0,
		Processed:     0,
		InputFile:     inputFilePath,
		OutputFile:    outputFilePath,
		KnowledgeFile: knowledgeFilePath,
		Threshold:     threshold,
		CreatedAt:     time.Now(),
		UpdatedAt:     time.Now(),
	}

	// 保存任务信息
	tasksMutex.Lock()
	tasks[taskID] = task
	tasksMutex.Unlock()

	// 异步执行分析任务
	go executeAnalysisTask(task)

	// 返回任务ID
	c.JSON(http.StatusOK, gin.H{
		"task_id": taskID,
		"status":  StatusPending,
	})
}

// 异步执行分析任务
func executeAnalysisTask(task *Task) {
	// 更新任务状态为处理中
	updateTaskStatus(task.ID, StatusProcessing, 0, 0, "")

	// 构建Python命令
	cmd := exec.Command(
		"python3",
		"../app.py",
		"--input", task.InputFile,
		"--output", task.OutputFile,
		"--knowledge", task.KnowledgeFile,
		"--threshold", fmt.Sprintf("%f", task.Threshold),
	)

	// 获取命令输出
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		updateTaskStatus(task.ID, StatusFailed, 0, 0, fmt.Sprintf("创建输出管道失败: %v", err))
		return
	}

	// 启动命令
	if err := cmd.Start(); err != nil {
		updateTaskStatus(task.ID, StatusFailed, 0, 0, fmt.Sprintf("启动分析任务失败: %v", err))
		return
	}

	// 读取输出并更新进度
	go monitorProgress(task.ID, stdout)

	// 等待命令完成
	if err := cmd.Wait(); err != nil {
		updateTaskStatus(task.ID, StatusFailed, 0, 0, fmt.Sprintf("分析任务执行失败: %v", err))
		return
	}

	// 检查输出文件是否存在
	if _, err := os.Stat(task.OutputFile); os.IsNotExist(err) {
		updateTaskStatus(task.ID, StatusFailed, 0, 0, "分析任务未生成结果文件")
		return
	}

	// 更新任务状态为完成
	tasksMutex.RLock()
	task, exists := tasks[task.ID]
	tasksMutex.RUnlock()

	if exists {
		updateTaskStatus(task.ID, StatusCompleted, task.Total, task.Total, "")
	}
}

// 监控进度输出
func monitorProgress(taskID string, stdout io.ReadCloser) {
	scanner := bufio.NewScanner(stdout)
	total := 0
	processed := 0

	for scanner.Scan() {
		line := scanner.Text()

		// 解析进度信息
		if strings.Contains(line, "共有") && strings.Contains(line, "条缺陷描述需要处理") {
			fmt.Sscanf(line, "共有 %d 条缺陷描述需要处理", &total)
			updateTaskStatus(taskID, StatusProcessing, total, processed, "")
		} else if strings.Contains(line, "正在处理第") && strings.Contains(line, "条缺陷描述") {
			fmt.Sscanf(line, "正在处理第 %d/%d 条缺陷描述", &processed, &total)
			updateTaskStatus(taskID, StatusProcessing, total, processed, "")
		} else if strings.Contains(line, "条处理完成") {
			processed++
			updateTaskStatus(taskID, StatusProcessing, total, processed, "")
		}
	}
}

// 更新任务状态
func updateTaskStatus(taskID, status string, total, processed int, errorMsg string) {
	tasksMutex.Lock()
	defer tasksMutex.Unlock()

	if task, exists := tasks[taskID]; exists {
		task.Status = status
		if total > 0 {
			task.Total = total
		}
		if processed > 0 || status == StatusCompleted {
			task.Processed = processed
		}
		if errorMsg != "" {
			task.Error = errorMsg
		}
		task.UpdatedAt = time.Now()
	}
}

// 获取任务状态
func getTaskStatus(c *gin.Context) {
	taskID := c.Param("id")

	tasksMutex.RLock()
	task, exists := tasks[taskID]
	tasksMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "任务不存在"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"id":        task.ID,
		"status":    task.Status,
		"total":     task.Total,
		"processed": task.Processed,
		"error":     task.Error,
	})
}

// 获取任务结果
func getTaskResults(c *gin.Context) {
	taskID := c.Param("id")

	tasksMutex.RLock()
	task, exists := tasks[taskID]
	tasksMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "任务不存在"})
		return
	}

	if task.Status != StatusCompleted {
		c.JSON(http.StatusBadRequest, gin.H{"error": "任务尚未完成"})
		return
	}

	// 读取Excel结果文件
	results, err := readExcelResults(task.OutputFile)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("读取结果文件失败: %v", err)})
		return
	}

	c.JSON(http.StatusOK, TaskResultsResponse{
		TaskID:  task.ID,
		Status:  task.Status,
		Results: results,
	})
}

// 读取Excel结果文件
func readExcelResults(filePath string) ([]AnalysisResult, error) {
	// 打开Excel文件
	f, err := excelize.OpenFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("打开Excel文件失败: %v", err)
	}
	defer f.Close()

	// 获取第一个工作表
	sheetName := f.GetSheetName(0)
	rows, err := f.GetRows(sheetName)
	if err != nil {
		return nil, fmt.Errorf("读取工作表失败: %v", err)
	}

	// 检查是否有数据
	if len(rows) <= 1 { // 只有表头或没有数据
		return []AnalysisResult{}, nil
	}

	// 查找列索引
	colIndexes := make(map[string]int)
	for i, cell := range rows[0] {
		colIndexes[cell] = i
	}

	// 检查必要的列是否存在
	if _, ok := colIndexes["缺陷描述"]; !ok {
		return nil, fmt.Errorf("Excel文件中缺少'缺陷描述'列")
	}
	if _, ok := colIndexes["分析结果"]; !ok {
		return nil, fmt.Errorf("Excel文件中缺少'分析结果'列")
	}

	// 解析数据
	results := make([]AnalysisResult, 0, len(rows)-1)
	for i := 1; i < len(rows); i++ {
		row := rows[i]
		if len(row) == 0 {
			continue
		}

		// 创建结果对象
		result := AnalysisResult{}

		// 设置标题（如果存在）
		if idx, ok := colIndexes["缺陷标题"]; ok && idx < len(row) {
			result.Title = row[idx]
		}

		// 设置描述
		if idx, ok := colIndexes["缺陷描述"]; ok && idx < len(row) {
			result.Description = row[idx]
		}

		// 设置评分分类
		if idx, ok := colIndexes["评分分类"]; ok && idx < len(row) {
			result.ScoreCategory = row[idx]
		}

		// 设置分析结果
		if idx, ok := colIndexes["分析结果"]; ok && idx < len(row) {
			result.Analysis = row[idx]
		}

		// 设置推理过程
		if idx, ok := colIndexes["推理过程"]; ok && idx < len(row) {
			result.Reasoning = row[idx]
		}

		// 添加到结果集
		results = append(results, result)
	}

	return results, nil
}

// 下载分析结果
func downloadResults(c *gin.Context) {
	taskID := c.Param("id")

	tasksMutex.RLock()
	task, exists := tasks[taskID]
	tasksMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "任务不存在"})
		return
	}

	if task.Status != StatusCompleted {
		c.JSON(http.StatusBadRequest, gin.H{"error": "任务尚未完成"})
		return
	}

	// 检查文件是否存在
	if _, err := os.Stat(task.OutputFile); os.IsNotExist(err) {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "结果文件不存在"})
		return
	}

	// 设置文件名
	fileName := fmt.Sprintf("缺陷分析结果_%s.xlsx", time.Now().Format("20060102150405"))
	c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=%s", fileName))
	c.Header("Content-Description", "File Transfer")
	c.File(task.OutputFile)
}
