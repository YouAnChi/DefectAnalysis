import streamlit as st
import subprocess
import os
import sys
import tempfile
import time
import threading
import queue
import logging
from pathlib import Path

# 设置页面标题和配置
st.set_page_config(
    page_title="智能缺陷分析系统",
    page_icon="🔍",
    layout="wide"
)

# 初始化session_state
if 'log_updated' not in st.session_state:
    st.session_state['log_updated'] = False
if 'output_data' not in st.session_state:
    st.session_state['output_data'] = None
if 'log_data' not in st.session_state:
    st.session_state['log_data'] = None
if 'analysis_completed' not in st.session_state:
    st.session_state['analysis_completed'] = False

# 创建一个队列用于存储日志信息
log_queue = queue.Queue()

# 定义一个函数来读取日志文件并将新行添加到队列中
def tail_log_file(log_file_path, q):
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # 移动到文件末尾
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    q.put(line)
                else:
                    time.sleep(0.1)
    except Exception as e:
        q.put(f"读取日志文件出错: {str(e)}")

# 主函数
def main():
    st.title("智能缺陷分析系统")
    
    # 添加说明
    st.markdown("""
    ### 使用说明
    1. 上传包含缺陷信息的Excel文件（必须包含"缺陷描述"列，可选包含"缺陷标题"和"评分分类"列）
    2. 点击"开始分析"按钮
    3. 等待分析完成后下载结果文件
    """)
    
    # 创建两列布局
    col1, col2 = st.columns([1, 1])
    
    # 如果分析已完成，显示下载按钮区域
    if st.session_state['analysis_completed']:
        st.success("分析已完成，可以下载结果文件和日志")
        download_col1, download_col2 = st.columns(2)
        
        with download_col1:
            if st.session_state['output_data'] is not None:
                st.download_button(
                    label="下载分析结果",
                    data=st.session_state['output_data'],
                    file_name="缺陷分析结果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_result"
                )
        
        with download_col2:
            if st.session_state['log_data'] is not None:
                st.download_button(
                    label="下载完整日志",
                    data=st.session_state['log_data'],
                    file_name="defect_analysis_full.log",
                    mime="text/plain",
                    key="download_log"
                )
    
    with col1:
        # 文件上传组件
        uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx", "xls"])
        
        # 使用固定的相似度阈值
        similarity_threshold = 0.3
        
        # 知识库文件选择（默认使用系统自带的）
        use_default_kb = st.checkbox("使用默认知识库", value=True)
        knowledge_base_file = None
        
        if not use_default_kb:
            knowledge_base_uploaded = st.file_uploader("上传知识库文件", type=["json"])
            if knowledge_base_uploaded:
                # 保存上传的知识库文件到临时文件
                temp_kb_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
                temp_kb_file.write(knowledge_base_uploaded.getvalue())
                knowledge_base_file = temp_kb_file.name
                temp_kb_file.close()
    
    # 获取当前脚本所在目录
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # 日志文件路径
    log_file_path = script_dir / "defect_analysis.log"
    
    # 处理按钮和日志显示
    if uploaded_file is not None:
        # 保存上传的文件到临时文件
        temp_input_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_input_file.write(uploaded_file.getvalue())
        input_file_path = temp_input_file.name
        temp_input_file.close()
        
        # 创建临时输出文件
        temp_output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        output_file_path = temp_output_file.name
        temp_output_file.close()
        
        # 处理按钮
        if st.button("开始分析"):
            # 清空日志队列
            while not log_queue.empty():
                log_queue.get()
            
            # 创建日志显示区域 - 使用容器以便更好地控制显示
            log_display_container = st.container()
            with log_display_container:
                st.subheader("处理日志（实时）")
                log_container = st.empty()
                
                # 添加自动滚动JavaScript代码
                st.markdown("""
                <script>
                    function scrollLogToBottom() {
                        const codeBlocks = parent.document.querySelectorAll('pre');
                        if (codeBlocks.length > 0) {
                            const lastCodeBlock = codeBlocks[codeBlocks.length - 1];
                            lastCodeBlock.scrollTop = lastCodeBlock.scrollHeight;
                        }
                    }
                    
                    // 每500毫秒检查一次并滚动
                    const scrollInterval = setInterval(scrollLogToBottom, 500);
                </script>
                """, unsafe_allow_html=True)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 启动日志监控线程
            log_thread = threading.Thread(
                target=tail_log_file, 
                args=(log_file_path, log_queue),
                daemon=True
            )
            log_thread.start()
            
            # 构建命令参数
            cmd = [sys.executable, str(script_dir / "app.py")]
            cmd.extend(["--input", input_file_path])
            cmd.extend(["--output", output_file_path])
            cmd.extend(["--threshold", str(similarity_threshold)])
            
            if knowledge_base_file:
                cmd.extend(["--knowledge", knowledge_base_file])
                
            # 检查上传的Excel文件中是否包含评分分类列
            try:
                import pandas as pd
                df = pd.read_excel(input_file_path)
                has_score_category = '评分分类' in df.columns
                if has_score_category:
                    st.info("检测到Excel文件包含评分分类列，将根据评分分类选择相应的系统提示词文件")
                    logging.info("检测到Excel文件包含评分分类列，将根据评分分类选择相应的系统提示词文件")
                    
                    # 这里不需要额外传递参数给app.py，因为app.py会自动检测Excel文件中的评分分类列
                    # 并为每一行数据根据其评分分类选择对应的系统提示词文件
                    st.info("系统将为每一行数据根据其评分分类选择对应的系统提示词文件")
            except Exception as e:
                st.warning(f"读取Excel文件时出错: {str(e)}，将使用默认系统提示词文件")
                logging.warning(f"读取Excel文件时出错: {str(e)}，将使用默认系统提示词文件")
            
            # 启动子进程
            with st.spinner("正在分析中..."):
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 显示日志信息
                all_logs = []
                completed = False
                start_time = time.time()
                max_log_lines = 30  # 限制显示的最大日志行数为30行
                
                try:
                    while True:
                        # 检查进程是否结束
                        if process.poll() is not None and log_queue.empty():
                            if not completed:
                                completed = True
                                status_text.text("分析完成！")
                                progress_bar.progress(1.0)
                            # 再等待一段时间确保所有日志都被读取
                            time.sleep(1)
                            if log_queue.empty():
                                break
                        
                        # 从队列中获取日志
                        new_logs_added = False
                        try:
                            while not log_queue.empty():
                                log_line = log_queue.get_nowait()
                                all_logs.append(log_line)
                                new_logs_added = True
                                # 如果日志行数超过最大限制，则保留最新的日志
                                if len(all_logs) > max_log_lines:
                                    all_logs = all_logs[-max_log_lines:]
                        except queue.Empty:
                            pass
                        
                        # 只有在有新日志添加时才更新显示，减少不必要的UI刷新
                        if new_logs_added and all_logs:
                            log_text = '\n'.join(all_logs)
                            log_container.code(log_text, language="")
                            # 强制滚动到最新日志
                            st.session_state['log_updated'] = True
                        
                        # 更新进度条（这里使用一个简单的基于时间的估计）
                        if not completed:
                            elapsed_time = time.time() - start_time
                            # 假设整个过程大约需要2分钟
                            estimated_progress = min(elapsed_time / 120, 0.99)
                            progress_bar.progress(estimated_progress)
                            status_text.text(f"分析中... 已用时 {int(elapsed_time)} 秒")
                        
                        time.sleep(0.1)
                except Exception as e:
                    st.error(f"处理过程中出错: {str(e)}")
                finally:
                    # 确保进程已终止
                    if process.poll() is None:
                        process.terminate()
                        process.wait()
                
                # 检查输出文件是否存在
                if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
                    # 读取输出文件
                    with open(output_file_path, "rb") as f:
                        output_data = f.read()
                    
                    # 将结果数据保存到session_state中，避免下载按钮刷新页面导致数据丢失
                    st.session_state['output_data'] = output_data
                    
                    # 如果日志文件存在，也保存到session_state中
                    if os.path.exists(log_file_path):
                        with open(log_file_path, "r", encoding="utf-8") as f:
                            log_data = f.read()
                        st.session_state['log_data'] = log_data
                    
                    # 标记分析已完成，用于显示下载按钮
                    st.session_state['analysis_completed'] = True
                    st.rerun()
                else:
                    st.error("分析过程中出错，未生成结果文件")
                
                # 清理临时文件
                try:
                    os.unlink(input_file_path)
                    os.unlink(output_file_path)
                    if knowledge_base_file and not use_default_kb:
                        os.unlink(knowledge_base_file)
                except Exception as e:
                    st.warning(f"清理临时文件失败: {str(e)}")
    
    with col2:
        # 显示系统状态和信息
        st.subheader("系统状态")
        
        # 检查必要文件是否存在
        app_py_exists = os.path.exists(script_dir / "app.py")
        kb_exists = os.path.exists(script_dir / "defects_knowledge_base.json")
        sys_prompt_exists = os.path.exists(script_dir / "sys.md")
        sys2_prompt_exists = os.path.exists(script_dir / "sys2.md")
        sys3_prompt_exists = os.path.exists(script_dir / "sys3.md")
        
        st.write(f"主程序文件: {'✅ 已找到' if app_py_exists else '❌ 未找到'}")
        st.write(f"默认知识库: {'✅ 已找到' if kb_exists else '❌ 未找到'}")
        st.write(f"系统提示文件(功能使用): {'✅ 已找到' if sys_prompt_exists else '❌ 未找到'}")
        st.write(f"系统提示文件(体验良好): {'✅ 已找到' if sys2_prompt_exists else '❌ 未找到'}")
        st.write(f"系统提示文件(性能效率): {'✅ 已找到' if sys3_prompt_exists else '❌ 未找到'}")
        
        # 添加使用说明
        st.subheader("操作提示")
        st.info("分析过程中，日志将在左侧实时显示。请耐心等待分析完成。分析完成后，可以同时下载分析结果和完整日志。")

if __name__ == "__main__":
    main()