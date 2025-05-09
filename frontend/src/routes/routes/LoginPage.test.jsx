"use client"

// src/context/WebSocketContext.test.jsx
import { useContext } from "react"
import { render, screen, act, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { WebSocketProvider, default as WebSocketContext } from "./WebSocketContext"

// --- Mock da API Global WebSocket ---
// Classe Mock para simular o comportamento do WebSocket
class MockWebSocket {
  static instances = [] // Rastrear instâncias criadas
  static mockClear() {
    MockWebSocket.instances = []
    MockWebSocket.prototype.send.mockClear()
    MockWebSocket.prototype.close.mockClear()
  }

  url = ""
  readyState = WebSocket.CONNECTING // Estado inicial
  onopen = vi.fn()
  onmessage = vi.fn()
  onerror = vi.fn()
  onclose = vi.fn()
  send = vi.fn()
  close = vi.fn((code = 1000, reason = "") => {
    // Simular fechamento limpo ou erro
    this.readyState = WebSocket.CLOSING
    setTimeout(() => {
      this.readyState = WebSocket.CLOSED
      this.onclose({ code, reason, wasClean: code === 1000 })
      MockWebSocket.instances = MockWebSocket.instances.filter((i) => i !== this) // Remover instância
    }, 5) // Pequeno delay
  })

  constructor(url) {
    this.url = url
    MockWebSocket.instances.push(this)
    // Simular conexão após um pequeno delay
    setTimeout(() => {
      if (this.readyState === WebSocket.CONNECTING) {
        // Simular falha se URL não tiver apiKey (teste simples)
        if (!url.includes("apiKey=test-api-key")) {
          // Usar chave de teste esperada
          this.readyState = WebSocket.CLOSED
          this.onerror(new Event("error")) // Disparar erro genérico
          this.onclose({ code: 1008, reason: "Invalid API Key (Mock)", wasClean: false })
        } else {
          this.readyState = WebSocket.OPEN
          this.onopen() // Chamar onopen simulando conexão
        }
      }
    }, 10)
  }

  // Método para simular recebimento de mensagem do servidor
  receiveMessage(data) {
    if (this.readyState === WebSocket.OPEN) {
      this.onmessage({ data: JSON.stringify(data) })
    }
  }

  // Método para simular desconexão pelo servidor
  simulateServerDisconnect(code = 1006, reason = "Server disconnected (Mock)", wasClean = false) {
    if (this.readyState === WebSocket.OPEN || this.readyState === WebSocket.CONNECTING) {
      this.readyState = WebSocket.CLOSING
      setTimeout(() => {
        this.readyState = WebSocket.CLOSED
        this.onclose({ code, reason, wasClean })
        MockWebSocket.instances = MockWebSocket.instances.filter((i) => i !== this)
      }, 5)
    }
  }
}

// Substituir WebSocket global pelo Mock
vi.stubGlobal("WebSocket", MockWebSocket)
// Configurar a API Key esperada para os testes
vi.stubEnv("VITE_STATIC_API_KEY", "test-api-key")
// Configurar URL WS
vi.stubEnv("VITE_WS_BASE_URL", "ws://test.socket.com/ws/updates")

// --- Componente Consumidor ---
function TestWsConsumer() {
  const context = useContext(WebSocketContext)
  if (!context) return <div>Error: Context is null</div>
  const { isConnected, lastJsonMessage, error, sendMessage, connectWebSocket, disconnectWebSocket } = context
  return (
    <div>
      <div data-testid="ws-status">{isConnected ? "Conectado" : "Desconectado"}</div>
      <div data-testid="ws-error">{error || "Nenhum erro WS"}</div>
      <div data-testid="ws-last-message">{lastJsonMessage ? JSON.stringify(lastJsonMessage) : "Nenhuma mensagem"}</div>
      <button onClick={() => sendMessage({ type: "ping" })}>Send Ping</button>
      <button onClick={connectWebSocket}>Connect</button>
      <button onClick={disconnectWebSocket}>Disconnect</button>
    </div>
  )
}

// --- Suite de Testes ---
describe("WebSocketContext", () => {
  beforeEach(() => {
    MockWebSocket.mockClear() // Limpar instâncias e mocks do WebSocket
    vi.useFakeTimers() // Usar timers falsos para controlar reconnect
  })

  afterEach(() => {
    vi.useRealTimers() // Restaurar timers reais
    vi.unstubAllEnvs() // Limpar mocks de env
  })

  it("initial state: disconnected, no error, no message", () => {
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Desconectado")
    expect(screen.getByTestId("ws-error")).toHaveTextContent("Nenhum erro WS")
    expect(screen.getByTestId("ws-last-message")).toHaveTextContent("Nenhuma mensagem")
  })

  it("connects automatically on mount if API Key is set", async () => {
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    // Esperar a simulação de conexão no MockWebSocket (10ms)
    await act(async () => {
      vi.advanceTimersByTime(15)
    })
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))
    expect(MockWebSocket.instances.length).toBe(1) // Verificar se uma instância foi criada
    expect(MockWebSocket.instances[0].url).toBe("ws://test.socket.com/ws/updates?apiKey=test-api-key")
  })

  it("fails to connect if API Key is missing", async () => {
    vi.stubEnv("VITE_STATIC_API_KEY", "") // Simular chave faltando
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    await act(async () => {
      vi.advanceTimersByTime(5)
    }) // Tempo para tentar conectar
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Desconectado")
    expect(screen.getByTestId("ws-error")).toHaveTextContent("Configuração de WebSocket ausente.")
    expect(MockWebSocket.instances.length).toBe(0) // Nenhuma instância deve ser criada
  })

  it("fails to connect if API Key is incorrect (simulated)", async () => {
    // O mock do WebSocket já simula isso se a key não for 'test-api-key'
    vi.stubEnv("VITE_STATIC_API_KEY", "wrong-key")
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    await act(async () => {
      vi.advanceTimersByTime(15)
    }) // Esperar tentativa e falha
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Desconectado"))
    expect(screen.getByTestId("ws-error")).toMatch(/Invalid API Key/i) // Verificar erro simulado
    expect(MockWebSocket.instances.length).toBe(0) // Instância é removida no mock após falha
  })

  it("sets lastJsonMessage when a valid message is received", async () => {
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    await act(async () => {
      vi.advanceTimersByTime(15)
    }) // Conectar
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))

    const testMessage = { type: "test_update", data: { value: 123 } }
    // Simular recebimento
    act(() => {
      MockWebSocket.instances[0]?.receiveMessage(testMessage)
    })

    await waitFor(() => {
      expect(screen.getByTestId("ws-last-message")).toHaveTextContent(JSON.stringify(testMessage))
    })
  })

  it("sends message when sendMessage is called and connected", async () => {
    const user = userEvent.setup()
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    await act(async () => {
      vi.advanceTimersByTime(15)
    }) // Conectar
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))

    const pingButton = screen.getByRole("button", { name: /send ping/i })
    const messageToSend = { type: "ping" }

    await act(async () => {
      await user.click(pingButton)
    })

    expect(MockWebSocket.instances[0].send).toHaveBeenCalledTimes(1)
    expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(JSON.stringify(messageToSend))
  })

  it("disconnects when disconnectWebSocket is called", async () => {
    const user = userEvent.setup()
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    await act(async () => {
      vi.advanceTimersByTime(15)
    }) // Conectar
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))

    const disconnectButton = screen.getByRole("button", { name: /disconnect/i })
    await act(async () => {
      await user.click(disconnectButton)
      vi.advanceTimersByTime(10) // Avançar timer para simular onclose
    })

    expect(MockWebSocket.instances[0]?.close).toHaveBeenCalledWith(1000, "User initiated disconnect")
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Desconectado"))
    expect(screen.getByTestId("ws-error")).toHaveTextContent("Nenhum erro WS") // Fechamento limpo
  })

  it("attempts to reconnect automatically on unclean disconnect", async () => {
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    await act(async () => {
      vi.advanceTimersByTime(15)
    }) // Conectar
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))
    expect(MockWebSocket.instances.length).toBe(1)

    // Simular desconexão não limpa do servidor
    act(() => {
      MockWebSocket.instances[0]?.simulateServerDisconnect(1006, "Server crash", false)
    })
    await act(async () => {
      vi.advanceTimersByTime(10)
    }) // Tempo para onclose rodar
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Desconectado"))
    expect(screen.getByTestId("ws-error")).toMatch(/Tentando reconectar.*Tentativa 1/i)

    // Avançar timer para a primeira tentativa de reconexão (5s)
    await act(async () => {
      vi.advanceTimersByTime(5010)
    })
    // Esperar conectar novamente (mock conecta em 10ms)
    await act(async () => {
      vi.advanceTimersByTime(15)
    })
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))
    expect(screen.getByTestId("ws-error")).toHaveTextContent("Nenhum erro WS") // Erro limpo após reconectar
    expect(MockWebSocket.instances.length).toBe(1) // Nova instância criada
  })

  it("gives up reconnecting after max attempts", async () => {
    render(
      <WebSocketProvider>
        <TestWsConsumer />
      </WebSocketProvider>,
    )
    await act(async () => {
      vi.advanceTimersByTime(15)
    }) // Conectar
    await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))

    const maxAttempts = 5 // Conforme definido no context
    for (let i = 1; i <= maxAttempts; i++) {
      // Simular desconexão
      act(() => {
        MockWebSocket.instances[0]?.simulateServerDisconnect(1006, `Disconnect ${i}`)
      })
      await act(async () => {
        vi.advanceTimersByTime(10)
      }) // Tempo para onclose
      await waitFor(() => expect(screen.getByTestId("ws-error")).toMatch(new RegExp(`Tentativa ${i}`, "i")))

      // Avançar timer para próxima tentativa
      const delay = 5000 * Math.pow(2, i - 1)
      await act(async () => {
        vi.advanceTimersByTime(delay + 5)
      }) // Tempo + margem
      // Conexão é refeita pelo mock
      await act(async () => {
        vi.advanceTimersByTime(15)
      })
      await waitFor(() => expect(screen.getByTestId("ws-status")).toHaveTextContent("Conectado"))
    }

    // Simular a 6ª desconexão (deve desistir)
    act(() => {
      MockWebSocket.instances[0]?.simulateServerDisconnect(1006, `Disconnect ${maxAttempts + 1}`)
    })
    await act(async () => {
      vi.advanceTimersByTime(10)
    }) // Tempo para onclose

    // Verificar se desistiu
    await waitFor(() => expect(screen.getByTestId("ws-error")).toMatch(/Máximo de tentativas.*atingido/i))
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Desconectado")

    // Avançar mais tempo para garantir que não tenta reconectar de novo
    await act(async () => {
      vi.advanceTimersByTime(30000)
    })
    expect(screen.getByTestId("ws-error")).toMatch(/Máximo de tentativas.*atingido/i) // Erro deve permanecer
  })
})
