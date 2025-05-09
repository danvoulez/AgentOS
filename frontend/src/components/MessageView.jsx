import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism"

/**
 * Componente para renderizar o conteúdo de uma mensagem com suporte a Markdown.
 * @param {string} content - Conteúdo da mensagem em formato Markdown
 * @param {string} emotion - Emoção associada à mensagem (opcional)
 */
const MessageView = ({ content, emotion }) => {
  // Se não houver conteúdo, retornar null
  if (!content) return null

  // Componentes customizados para o ReactMarkdown
  const components = {
    // Customizar renderização de código
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || "")
      const language = match ? match[1] : ""

      return !inline ? (
        <div className="my-4 rounded-md overflow-hidden">
          <div className="bg-fusion-deep/80 px-4 py-1 text-xs text-fusion-light flex justify-between items-center">
            <span>{language || "code"}</span>
          </div>
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={language}
            PreTag="div"
            className="rounded-b-md"
            showLineNumbers
            {...props}
          >
            {String(children).replace(/\n$/, "")}
          </SyntaxHighlighter>
        </div>
      ) : (
        <code className="bg-fusion-deep/50 px-1 py-0.5 rounded text-sm" {...props}>
          {children}
        </code>
      )
    },

    // Customizar links
    a({ node, children, href, ...props }) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-fusion-purple hover:underline"
          {...props}
        >
          {children}
        </a>
      )
    },

    // Customizar listas
    ul({ node, children, ...props }) {
      return (
        <ul className="list-disc pl-6 my-2 space-y-1" {...props}>
          {children}
        </ul>
      )
    },

    ol({ node, children, ...props }) {
      return (
        <ol className="list-decimal pl-6 my-2 space-y-1" {...props}>
          {children}
        </ol>
      )
    },

    // Customizar cabeçalhos
    h1({ node, children, ...props }) {
      return (
        <h1 className="text-xl font-bold my-3" {...props}>
          {children}
        </h1>
      )
    },

    h2({ node, children, ...props }) {
      return (
        <h2 className="text-lg font-bold my-2" {...props}>
          {children}
        </h2>
      )
    },

    h3({ node, children, ...props }) {
      return (
        <h3 className="text-base font-bold my-2" {...props}>
          {children}
        </h3>
      )
    },

    // Customizar blockquote
    blockquote({ node, children, ...props }) {
      return (
        <blockquote className="border-l-4 border-fusion-purple/50 pl-4 py-1 my-2 text-fusion-light italic" {...props}>
          {children}
        </blockquote>
      )
    },

    // Customizar tabelas
    table({ node, children, ...props }) {
      return (
        <div className="overflow-x-auto my-4">
          <table className="min-w-full divide-y divide-fusion-medium/50" {...props}>
            {children}
          </table>
        </div>
      )
    },

    thead({ node, children, ...props }) {
      return (
        <thead className="bg-fusion-medium/30" {...props}>
          {children}
        </thead>
      )
    },

    tbody({ node, children, ...props }) {
      return (
        <tbody className="divide-y divide-fusion-medium/30" {...props}>
          {children}
        </tbody>
      )
    },

    tr({ node, children, ...props }) {
      return (
        <tr className="hover:bg-fusion-medium/10" {...props}>
          {children}
        </tr>
      )
    },

    th({ node, children, ...props }) {
      return (
        <th className="px-3 py-2 text-left text-xs font-medium text-fusion-light uppercase tracking-wider" {...props}>
          {children}
        </th>
      )
    },

    td({ node, children, ...props }) {
      return (
        <td className="px-3 py-2 text-sm" {...props}>
          {children}
        </td>
      )
    },
  }

  return (
    <div className="markdown-content text-sm leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default MessageView
