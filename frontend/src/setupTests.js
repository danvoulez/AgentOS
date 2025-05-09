// src/setupTests.js
import "@testing-library/jest-dom" // Importa os matchers jest-dom
import { vi, afterEach } from "vitest" // Importar vi e afterEach

// --- Mocks Globais ---

// Mock localStorage
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value.toString()
    },
    removeItem: (key) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
    key: (index) => Object.keys(store)[index] || null,
    get length() {
      return Object.keys(store).length
    },
  }
})()
Object.defineProperty(window, "localStorage", { value: localStorageMock, writable: true })
Object.defineProperty(window, "sessionStorage", { value: localStorageMock, writable: true }) // Mock sessionStorage too if used

// Mock window.confirm
window.confirm = vi.fn(() => true) // Default mock to return true (confirm)

// Mock window.alert
window.alert = vi.fn()

// Mock window.matchMedia (necessário para alguns componentes de UI/libs como antd, chakra, etc.)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated but needed for some libs
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver (used by Framer Motion's viewport features, etc.)
const IntersectionObserverMock = vi.fn(() => ({
  disconnect: vi.fn(),
  observe: vi.fn(),
  unobserve: vi.fn(),
  takeRecords: vi.fn(),
}))
vi.stubGlobal("IntersectionObserver", IntersectionObserverMock)

// Mock ResizeObserver (used by some layout components/hooks)
const ResizeObserverMock = vi.fn(() => ({
  disconnect: vi.fn(),
  observe: vi.fn(),
  unobserve: vi.fn(),
}))
vi.stubGlobal("ResizeObserver", ResizeObserverMock)

// --- Limpeza Após Testes ---

// Limpar todos os mocks e localStorage após cada teste
afterEach(() => {
  vi.clearAllMocks()
  // Reset any specific mocks if needed (e.g., window.confirm to return false sometimes)
  // window.confirm.mockClear().mockReturnValue(true); // Example reset
  localStorage.clear()
  sessionStorage.clear()
})

console.log("Vitest Global Test Setup Complete.") // Confirmação no console de teste
