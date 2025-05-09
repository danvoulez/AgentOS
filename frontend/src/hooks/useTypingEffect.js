"use client"

import { useState, useEffect, useRef } from "react"

/**
 * Hook customizado para criar um efeito de digitação em um texto.
 * @param {string} fullText O texto completo a ser digitado.
 * @param {number} typingSpeed Velocidade de digitação em milissegundos por caractere.
 * @returns {{displayedText: string, isComplete: boolean}} Objeto contendo o texto exibido atualmente e um booleano indicando se a digitação está completa.
 */
export const useTypingEffect = (fullText = "", typingSpeed = 20) => {
  const [displayedText, setDisplayedText] = useState("")
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const intervalRef = useRef(null)

  // Resetar efeito quando o texto completo mudar
  useEffect(() => {
    // Limpar intervalo anterior se houver
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    // Resetar estados
    setDisplayedText("")
    setCurrentIndex(0)
    setIsComplete(false)

    // Iniciar novo intervalo apenas se houver texto
    if (fullText && fullText.length > 0 && typingSpeed > 0) {
      // Usar setTimeout para o primeiro caractere para evitar delay inicial 0
      const firstCharTimeout = setTimeout(() => {
        setDisplayedText(fullText[0])
        setCurrentIndex(1)
      }, typingSpeed)

      intervalRef.current = setInterval(() => {
        setCurrentIndex((prevIndex) => {
          const nextIndex = prevIndex + 1
          if (nextIndex > fullText.length) {
            // Digitação concluída
            clearInterval(intervalRef.current)
            intervalRef.current = null
            setIsComplete(true)
            setDisplayedText(fullText) // Garantir que texto final está completo
            return prevIndex // Manter índice final
          }
          // Atualizar texto exibido
          setDisplayedText(fullText.substring(0, nextIndex))
          return nextIndex
        })
      }, typingSpeed)

      // Cleanup para o primeiro timeout
      return () => clearTimeout(firstCharTimeout)
    } else {
      // Se não houver texto ou velocidade inválida, marcar como completo imediatamente
      setIsComplete(true)
      setDisplayedText(fullText) // Exibir texto completo se já fornecido
    }

    // Cleanup do intervalo principal
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [fullText, typingSpeed]) // Dependências: re-executar se texto ou velocidade mudarem

  return { displayedText, isComplete }
}
