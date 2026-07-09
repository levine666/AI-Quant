/** 检测 file:// 协议并提示使用本地服务器 */
function guardFileProtocol() {
  if (location.protocol !== "file:") return true;
  const msg = "无法通过双击 HTML 加载数据（浏览器限制 fetch）。请运行：python3 AI-Quant/run.py serve";
  const loading = document.getElementById("loading");
  if (loading) {
    loading.classList.remove("hidden");
    loading.textContent = msg;
  }
  const toast = document.getElementById("toast");
  if (toast) {
    toast.textContent = msg;
    toast.className = "toast toast-error";
  }
  return false;
}
