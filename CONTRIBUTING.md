# CONTRIBUTING.md

Obrigado por contribuir com o AgentOS! Este projeto segue um modelo modular e auditável.  
Toda colaboração deve respeitar os princípios de clareza, reversibilidade e auditabilidade.

## Requisitos

- Node.js + Yarn
- Docker e Docker Compose
- Poetry (para ambientes Python, se aplicável)
- Conta de desenvolvedor Stripe (para testes locais)

## Como contribuir

1. Faça um fork do repositório
2. Crie uma branch com nome claro: `feature/<sua-feature>` ou `fix/<correcao>`
3. Faça commits pequenos e com mensagens claras
4. Crie um Pull Request com descrição objetiva

## Padrões de código

- Frontend: React + Tailwind, estado com Zustand
- Backend: Express.js com controllers e services claros
- Evite lógica acoplada entre rotas e modelos

## Testes

Ainda não há cobertura completa.  
Ideal: Jest no backend, Cypress no frontend.

## Comunicação

Use comentários nos PRs, mantenha a linha do tempo limpa.  
Documente decisões técnicas no README ou `DECISIONS.md` (se criado).