"use client"

import { useRef, useEffect } from "react"

/**
 * Hook customizado que retorna uma ref para ser anexada a um container scrollável.
 * Ele rola o container para o final sempre que o valor da dependência mudar.
 * @param {any} dependency A dependência que dispara o scroll (ex: lista de mensagens).
 * @returns {React.RefObject} A ref a ser anexada ao elemento container.
 */
export const useScrollToBottom = (dependency) => {
  const scrollContainerRef = useRef(null)

  useEffect(() => {
    const scrollElement = scrollContainerRef.current
    if (scrollElement) {
      // console.debug('Scrolling to bottom triggered by dependency change.');
      // Usar scrollIntoView no último filho ou definir scrollTop
      // scrollElement.scrollTop = scrollElement.scrollHeight;
      // Alternativa: usar scrollIntoView no último filho (pode ser mais suave)
      const lastChild = scrollElement.lastElementChild
      if (lastChild) {
        // Usar { behavior: 'smooth' } pode causar problemas se o conteúdo
        // for adicionado muito rapidamente. 'auto' ou 'instant' é mais confiável.
        lastChild.scrollIntoView({ behavior: "auto", block: "end" })
        // console.debug('Scrolled last child into view.');
      } else {
        // Fallback se não houver filhos (ex: ao limpar mensagens)
        scrollElement.scrollTop = scrollElement.scrollHeight
        // console.debug('Scrolling to bottom using scrollTop.');
      }
    }
  }, [dependency]) // Disparar efeito quando a dependência mudar

  return scrollContainerRef
}
