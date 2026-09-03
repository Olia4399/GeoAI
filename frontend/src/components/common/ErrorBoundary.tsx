import { Component, type ReactNode } from "react";

/* ================================================================
   React 渲染错误兜底：子组件抛异常时展示错误信息与刷新按钮，
   避免整棵组件树白屏且无任何提示
   ================================================================ */

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error("[ErrorBoundary] 渲染错误:", error);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            gap: 10,
            color: "#666",
            padding: 20,
          }}
        >
          <div style={{ fontSize: 32 }}>💥</div>
          <div style={{ fontWeight: 600, fontSize: 15, color: "#1a1a1a" }}>
            界面渲染出错
          </div>
          <div
            style={{
              fontSize: 12,
              color: "#999",
              maxWidth: 480,
              wordBreak: "break-all",
              textAlign: "center",
              fontFamily: "Consolas, Monaco, monospace",
              lineHeight: 1.6,
            }}
          >
            {this.state.error.message}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: "6px 16px",
              borderRadius: 6,
              border: "1px solid #1a237e",
              background: "#fff",
              color: "#1a237e",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            🔄 刷新页面
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
