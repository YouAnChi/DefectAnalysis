// 全局变量
let analysisResults = [];
let currentTaskId = null;
let pollingInterval = null;

// DOM元素
const uploadForm = document.getElementById('upload-form');
const fileUpload = document.getElementById('file-upload');
const knowledgeBase = document.getElementById('knowledge-base');
const customKnowledge = document.getElementById('custom-knowledge');
const analyzeBtn = document.getElementById('analyze-btn');
const progressSection = document.querySelector('.progress-section');
const progressBar = document.querySelector('.progress-bar .progress');
const progressText = document.querySelector('.progress-text');
const resultsSection = document.querySelector('.results-section');
const downloadBtn = document.getElementById('download-btn');
const viewDetailsBtn = document.getElementById('view-details-btn');
const totalCount = document.getElementById('total-count');
const successCount = document.getElementById('success-count');
const failCount = document.getElementById('fail-count');
const resultsBody = document.getElementById('results-body');
const detailModal = new bootstrap.Modal(document.getElementById('detail-modal'));
// Bootstrap 5 不需要关闭按钮的引用，使用data-bs-dismiss属性自动处理

// API基础URL
const API_BASE_URL = 'http://localhost:8080/api';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化事件监听器
    initEventListeners();
});

// 初始化所有事件监听器
function initEventListeners() {
    // 知识库选择事件
    knowledgeBase.addEventListener('change', () => {
        if (knowledgeBase.value === 'custom') {
            customKnowledge.style.display = 'block';
        } else {
            customKnowledge.style.display = 'none';
        }
    });

    // 表单提交事件
    uploadForm.addEventListener('submit', handleFormSubmit);

    // 下载结果按钮事件
    downloadBtn.addEventListener('click', downloadResults);

    // 查看详情按钮事件
    viewDetailsBtn.addEventListener('click', () => {
        // 显示第一条结果的详情
        if (analysisResults.length > 0) {
            showDetailModal(analysisResults[0]);
        }
    });

    // 关闭模态框事件
    closeModal.addEventListener('click', () => {
        detailModal.style.display = 'none';
    });

    // 点击模态框外部关闭
    window.addEventListener('click', (event) => {
        if (event.target === detailModal) {
            detailModal.style.display = 'none';
        }
    });
}

// 处理表单提交
async function handleFormSubmit(event) {
    event.preventDefault();
    
    // 验证文件上传
    if (!fileUpload.files[0]) {
        alert('请选择Excel文件');
        return;
    }
    
    // 准备表单数据
    const formData = new FormData();
    formData.append('file', fileUpload.files[0]);
    
    // 添加知识库文件
    if (knowledgeBase.value === 'custom' && customKnowledge.files[0]) {
        formData.append('knowledge_base', customKnowledge.files[0]);
    } else {
        formData.append('knowledge_base_name', knowledgeBase.value);
    }
    
    // 使用默认相似度阈值
    formData.append('threshold', '0.3');
    
    try {
        // 显示进度区域，隐藏结果区域
        progressSection.style.display = 'block';
        resultsSection.style.display = 'none';
        progressBar.style.width = '0%';
        progressText.textContent = '准备分析...';
        
        // 禁用提交按钮
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '分析中...';
        
        // 发送分析请求
        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`服务器错误: ${response.status}`);
        }
        
        const data = await response.json();
        currentTaskId = data.task_id;
        
        // 开始轮询任务状态
        startPolling(currentTaskId);
        
    } catch (error) {
        console.error('提交分析请求失败:', error);
        alert(`提交分析请求失败: ${error.message}`);
        resetForm();
    }
}

// 开始轮询任务状态
function startPolling(taskId) {
    // 清除之前的轮询
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/task/${taskId}`);
            if (!response.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }
            
            const data = await response.json();
            updateProgress(data);
            
            // 如果任务完成，停止轮询
            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(pollingInterval);
                
                if (data.status === 'completed') {
                    // 获取完整结果
                    fetchResults(taskId);
                } else {
                    alert('分析任务失败，请重试');
                    resetForm();
                }
            }
        } catch (error) {
            console.error('获取任务状态失败:', error);
            clearInterval(pollingInterval);
            alert(`获取任务状态失败: ${error.message}`);
            resetForm();
        }
    }, 2000); // 每2秒轮询一次
}

// 更新进度显示
function updateProgress(data) {
    if (data.total > 0) {
        const percentage = Math.round((data.processed / data.total) * 100);
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${data.processed}/${data.total} 条缺陷已分析`;
    }
}

// 获取完整分析结果
async function fetchResults(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/results/${taskId}`);
        if (!response.ok) {
            throw new Error(`服务器错误: ${response.status}`);
        }
        
        const data = await response.json();
        analysisResults = data.results;
        
        // 显示结果
        displayResults(analysisResults);
        
    } catch (error) {
        console.error('获取分析结果失败:', error);
        alert(`获取分析结果失败: ${error.message}`);
        resetForm();
    }
}

// 显示分析结果
function displayResults(results) {
    // 隐藏进度区域，显示结果区域
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // 更新统计信息
    const total = results.length;
    const success = results.filter(r => !r.error).length;
    const fail = total - success;
    
    totalCount.textContent = total;
    successCount.textContent = success;
    failCount.textContent = fail;
    
    // 清空结果表格
    resultsBody.innerHTML = '';
    
    // 填充结果表格
    results.forEach((result, index) => {
        const row = document.createElement('tr');
        
        // 序号
        const indexCell = document.createElement('td');
        indexCell.textContent = index + 1;
        row.appendChild(indexCell);
        
        // 缺陷标题
        const titleCell = document.createElement('td');
        titleCell.textContent = result.title || '无标题';
        row.appendChild(titleCell);
        
        // 评分分类
        const categoryCell = document.createElement('td');
        categoryCell.textContent = result.score_category || '未分类';
        row.appendChild(categoryCell);
        
        // 分析结果
        const analysisCell = document.createElement('td');
        if (result.error) {
            analysisCell.textContent = '分析失败';
            analysisCell.classList.add('text-danger');
        } else {
            // 截取前50个字符
            const shortAnalysis = result.analysis.length > 50 
                ? result.analysis.substring(0, 50) + '...' 
                : result.analysis;
            analysisCell.textContent = shortAnalysis;
        }
        row.appendChild(analysisCell);
        
        // 操作按钮
        const actionCell = document.createElement('td');
        const viewBtn = document.createElement('button');
        viewBtn.innerHTML = '<i class="fas fa-eye me-1"></i>详情';
        viewBtn.className = 'btn btn-sm btn-outline-primary';
        viewBtn.addEventListener('click', () => showDetailModal(result));
        actionCell.appendChild(viewBtn);
        row.appendChild(actionCell);
        
        resultsBody.appendChild(row);
    });
    
    // 重置表单
    resetForm();
}

// 显示详情模态框
function showDetailModal(result) {
    document.getElementById('detail-title').textContent = result.title || '无标题';
    document.getElementById('detail-description').textContent = result.description || '无描述';
    document.getElementById('detail-category').textContent = result.score_category || '未分类';
    
    if (result.error) {
        document.getElementById('detail-analysis').textContent = '分析失败: ' + result.error;
        document.getElementById('detail-reasoning').textContent = '无推理过程';
    } else {
        document.getElementById('detail-analysis').textContent = result.analysis || '无分析结果';
        document.getElementById('detail-reasoning').textContent = result.reasoning || '无推理过程';
    }
    
    // 使用Bootstrap的Modal方法显示模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('detail-modal')) || detailModal;
    modal.show();
}

// 下载分析结果
function downloadResults() {
    if (analysisResults.length === 0) {
        alert('没有可下载的结果');
        return;
    }
    
    // 发起下载请求
    window.location.href = `${API_BASE_URL}/download/${currentTaskId}`;
}

// 重置表单状态
function resetForm() {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = '开始分析';
}