/**
 * Componente simples de spinner de carregamento usando Tailwind CSS.
 * @param {string} className - Classes CSS adicionais para customização.
 * @param {string} size - Define o tamanho (ex: 'w-8 h-8'). Default 'w-6 h-6'.
 * @param {string} color - Define a cor da borda (ex: 'border-fusion-purple'). Default 'border-fusion-purple'.
 */
const LoadingSpinner = ({ className = "", size = "w-6 h-6", color = "border-fusion-purple" }) => {
  return (
    <div
      className={`inline-block animate-spin rounded-full border-4 border-solid ${color} border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite] ${size} ${className}`}
      role="status"
      aria-label="loading" // Adicionar acessibilidade
    >
      <span className="!absolute !-m-px !h-px !w-px !overflow-hidden !whitespace-nowrap !border-0 !p-0 ![clip:rect(0,0,0,0)]">
        Carregando...
      </span>
    </div>
  )
}

export default LoadingSpinner
