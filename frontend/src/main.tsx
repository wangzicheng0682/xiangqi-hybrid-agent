import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// 临时禁用 StrictMode 来验证 SSE 延迟问题
// StrictMode 在开发环境会导致组件双重渲染，可能造成连接泄漏
ReactDOM.createRoot(document.getElementById('root')!).render(
  // <React.StrictMode>
    <App />
  // </React.StrictMode>,
)
