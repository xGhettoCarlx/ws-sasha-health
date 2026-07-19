import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center p-8 text-center min-h-[50vh]">
          <div
            className="rounded-2xl p-6 max-w-sm w-full"
            style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)" }}
          >
            <p
              className="text-lg font-semibold mb-2"
              style={{ color: "var(--tg-theme-text-color)" }}
            >
              Что-то пошло не так
            </p>
            <p
              className="text-sm mb-4"
              style={{ color: "var(--tg-theme-hint-color)" }}
            >
              {this.state.error?.message || "Неизвестная ошибка"}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="rounded-xl px-4 py-2 text-sm font-medium transition-opacity hover:opacity-80"
              style={{ background: "#60A5FA", color: "#fff" }}
            >
              Попробовать снова
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
