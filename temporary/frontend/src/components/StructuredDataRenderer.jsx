"use client"
import { motion } from "framer-motion"

/**
 * Componente para renderizar dados estruturados de forma adequada.
 * Suporta diferentes tipos de dados estruturados como tabelas, listas, etc.
 * @param {Object} data - Dados estruturados a serem renderizados
 */
const StructuredDataRenderer = ({ data }) => {
  // Se não houver dados, retornar mensagem de erro
  if (!data) {
    return <div className="text-fusion-error">Dados estruturados inválidos ou vazios</div>
  }

  // Detectar o tipo de dados estruturados
  const detectDataType = () => {
    if (Array.isArray(data)) {
      if (data.length > 0 && typeof data[0] === "object") {
        return "table"
      }
      return "list"
    }

    if (typeof data === "object") {
      if (data.type === "table" && Array.isArray(data.rows)) {
        return "explicit-table"
      }
      if (data.type === "chart") {
        return "chart"
      }
      return "object"
    }

    return "unknown"
  }

  const dataType = detectDataType()

  // Renderizar tabela
  const renderTable = (tableData) => {
    // Extrair todas as chaves possíveis dos objetos
    const allKeys = Array.from(new Set(tableData.flatMap((item) => Object.keys(item))))

    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-fusion-medium/50">
          <thead>
            <tr>
              {allKeys.map((key) => (
                <th
                  key={key}
                  className="px-3 py-2 text-left text-xs font-medium text-fusion-light uppercase tracking-wider bg-fusion-medium/30"
                >
                  {key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-fusion-medium/30">
            {tableData.map((row, rowIndex) => (
              <tr key={rowIndex} className={rowIndex % 2 === 0 ? "bg-fusion-medium/10" : ""}>
                {allKeys.map((key) => (
                  <td key={`${rowIndex}-${key}`} className="px-3 py-2 text-sm">
                    {row[key] !== undefined ? String(row[key]) : "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // Renderizar lista
  const renderList = (listData) => {
    return (
      <ul className="list-disc pl-5 space-y-1">
        {listData.map((item, index) => (
          <li key={index} className="text-sm">
            {typeof item === "object" ? JSON.stringify(item) : String(item)}
          </li>
        ))}
      </ul>
    )
  }

  // Renderizar objeto
  const renderObject = (objectData) => {
    return (
      <div className="bg-fusion-deep/30 p-3 rounded-md">
        <pre className="text-xs overflow-x-auto whitespace-pre-wrap break-words">
          {JSON.stringify(objectData, null, 2)}
        </pre>
      </div>
    )
  }

  // Renderizar tabela explícita
  const renderExplicitTable = (tableData) => {
    const { headers, rows } = tableData

    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-fusion-medium/50">
          {headers && (
            <thead>
              <tr>
                {headers.map((header, index) => (
                  <th
                    key={index}
                    className="px-3 py-2 text-left text-xs font-medium text-fusion-light uppercase tracking-wider bg-fusion-medium/30"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody className="divide-y divide-fusion-medium/30">
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className={rowIndex % 2 === 0 ? "bg-fusion-medium/10" : ""}>
                {row.map((cell, cellIndex) => (
                  <td key={`${rowIndex}-${cellIndex}`} className="px-3 py-2 text-sm">
                    {cell !== undefined ? String(cell) : "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // Renderizar com base no tipo de dados
  const renderContent = () => {
    switch (dataType) {
      case "table":
        return renderTable(data)
      case "list":
        return renderList(data)
      case "explicit-table":
        return renderExplicitTable(data)
      case "chart":
        return <div className="text-fusion-light">Visualização de gráfico não disponível</div>
      case "object":
      default:
        return renderObject(data)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="structured-data-container"
    >
      {renderContent()}
    </motion.div>
  )
}

export default StructuredDataRenderer
