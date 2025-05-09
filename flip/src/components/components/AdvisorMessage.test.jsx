import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import StructuredDataRenderer from "./StructuredDataRenderer"

// Mock do SyntaxHighlighter para verificar props passadas
vi.mock("react-syntax-highlighter", () => ({
  Prism: ({ children, language, style }) => (
    <pre data-testid="syntax-highlighter" data-language={language} data-style={JSON.stringify(style)}>
      <code>{children}</code>
    </pre>
  ),
}))
vi.mock("react-syntax-highlighter/dist/esm/styles/prism", () => ({
  atomDark: { mockStyle: "atomDark" }, // Mock simples do objeto de estilo
}))

// Mock do ReactMarkdown e remarkGfm para verificar se são chamados
const mockReactMarkdown = vi.fn(({ children }) => <div data-testid="react-markdown">{children}</div>)
vi.mock("react-markdown", () => ({ default: mockReactMarkdown }))
vi.mock("remark-gfm", () => ({
  default: () => {
    /* mock plugin */
  },
}))

describe("StructuredDataRenderer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders a Markdown table for an array of objects", () => {
    const data = [
      { id: 1, name: "Item A", price: 10.5, category: "X" },
      { id: 2, name: "Item B", price: 25.0, category: "Y" },
      { id: 3, name: "Item C | Pipe", price: 5.0, category: "X", extra: "data" }, // Incluir pipe
    ]
    render(<StructuredDataRenderer data={data} />)

    // Verificar se ReactMarkdown foi chamado
    expect(mockReactMarkdown).toHaveBeenCalled()

    // Verificar o conteúdo Markdown gerado (dentro do mock)
    const markdownContent = mockReactMarkdown.mock.calls[0][0].children // Pega o prop 'children'
    expect(markdownContent).toContain("| id | name | price | category | extra |") // Header
    expect(markdownContent).toContain("| --- | --- | --- | --- | --- |") // Separator
    expect(markdownContent).toContain("| 1 | Item A | 10.5 | X | *null* |") // Row 1 (null for missing 'extra')
    expect(markdownContent).toContain("| 2 | Item B | 25.0 | Y | *null* |") // Row 2
    expect(markdownContent).toContain("| 3 | Item C | Pipe | 5.0 | X | data |") // Row 3 (pipe escaped)

    // Verificar se o container tem overflow
    const markdownContainer = screen.getByTestId("react-markdown").parentElement
    expect(markdownContainer).toHaveClass("overflow-x-auto")
  })

  it("renders formatted JSON using SyntaxHighlighter for a simple object", () => {
    const data = { user: "test", role: "admin", last_login: "2024-05-15T12:00:00Z" }
    render(<StructuredDataRenderer data={data} />)

    // Verificar se SyntaxHighlighter foi chamado
    const highlighter = screen.getByTestId("syntax-highlighter")
    expect(highlighter).toBeInTheDocument()
    expect(highlighter).toHaveAttribute("data-language", "json")
    expect(highlighter).toHaveAttribute("data-style", JSON.stringify({ mockStyle: "atomDark" })) // Verificar estilo mockado

    // Verificar conteúdo
    expect(highlighter).toHaveTextContent(JSON.stringify(data, null, 2))

    // Verificar que ReactMarkdown NÃO foi chamado
    expect(mockReactMarkdown).not.toHaveBeenCalled()
  })

  it("renders formatted JSON using SyntaxHighlighter for non-object/array data (fallback)", () => {
    const dataString = "Just a simple string"
    const dataNumber = 12345
    const dataNull = null

    const { rerender } = render(<StructuredDataRenderer data={dataString} />)
    let highlighter = screen.getByTestId("syntax-highlighter")
    expect(highlighter).toHaveTextContent(JSON.stringify(dataString, null, 2))
    expect(highlighter).toHaveAttribute("data-language", "json")

    rerender(<StructuredDataRenderer data={dataNumber} />)
    highlighter = screen.getByTestId("syntax-highlighter")
    expect(highlighter).toHaveTextContent(JSON.stringify(dataNumber, null, 2))
    expect(highlighter).toHaveAttribute("data-language", "json")

    rerender(<StructuredDataRenderer data={dataNull} />)
    highlighter = screen.getByTestId("syntax-highlighter")
    expect(highlighter).toHaveTextContent(JSON.stringify(dataNull, null, 2)) // "null"
    expect(highlighter).toHaveAttribute("data-language", "json")
  })

  it("renders placeholder for empty array", () => {
    render(<StructuredDataRenderer data={[]} />)
    expect(screen.getByText("[Array of Empty Objects]")).toBeInTheDocument() // Atualizado baseado no código
    expect(screen.queryByTestId("react-markdown")).not.toBeInTheDocument()
    expect(screen.queryByTestId("syntax-highlighter")).not.toBeInTheDocument()
  })

  it("renders placeholder for empty object", () => {
    render(<StructuredDataRenderer data={{}} />)
    const codeElement = screen.getByText("{ }").closest("code") // O texto está dentro de <code>
    expect(codeElement).toBeInTheDocument()
    expect(screen.queryByTestId("react-markdown")).not.toBeInTheDocument()
    expect(screen.queryByTestId("syntax-highlighter")).not.toBeInTheDocument() // Não usa highlighter para objeto vazio
  })

  it("handles objects nested within table cells", () => {
    const data = [{ id: 1, details: { nested: true, value: 10 } }]
    render(<StructuredDataRenderer data={data} />)
    const markdownContent = mockReactMarkdown.mock.calls[0][0].children
    expect(markdownContent).toContain("| 1 | `[Object]` |") // Verifica placeholder para objeto
  })

  it("escapes pipe characters in table headers and cells", () => {
    const data = [{ "Header|Pipe": "Value|Pipe" }]
    render(<StructuredDataRenderer data={data} />)
    const markdownContent = mockReactMarkdown.mock.calls[0][0].children
    expect(markdownContent).toContain("| Header|Pipe |") // Header escapado
    expect(markdownContent).toContain("| Value|Pipe |") // Célula escapada
  })

  it("truncates long cell values in tables", () => {
    const longText = "a".repeat(100)
    const expectedTruncated = longText.substring(0, 70) + "..." // Conforme MAX_CELL_LENGTH = 70
    const data = [{ id: 1, long: longText }]
    render(<StructuredDataRenderer data={data} />)
    const markdownContent = mockReactMarkdown.mock.calls[0][0].children
    expect(markdownContent).toContain(`| 1 | ${expectedTruncated} |`)
  })
})
