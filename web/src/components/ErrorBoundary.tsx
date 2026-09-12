import { Component, ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallbackTitle?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in UI component:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="m-4 rounded-md border border-signal-bad/40 bg-signal-bad/[0.08] p-5 text-graphite dark:text-bone">
          <div className="flex items-center gap-2 font-mono text-sm font-bold text-signal-bad">
            <span>⚠️</span>
            <span>{this.props.fallbackTitle || 'Component Render Error Intercepted'}</span>
          </div>
          <p className="mt-2 font-mono text-xs text-graphite-soft dark:text-bone">
            {this.state.error?.message || 'An unexpected runtime error occurred.'}
          </p>
          <div className="mt-4 flex gap-3">
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="rounded bg-signal-bad px-3 py-1 font-mono text-xs font-semibold text-white hover:bg-signal-bad/80"
            >
              Retry Rendering
            </button>
            <button
              onClick={() => window.location.reload()}
              className="rounded border border-bone-edge px-3 py-1 font-mono text-xs text-graphite hover:text-bone dark:border-stage-line"
            >
              Reload Console
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
