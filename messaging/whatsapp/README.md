# WhatsApp Integration para AgentOS

Esta integração permite que o VoxAgent se comunique através do WhatsApp, usando uma abordagem de cliente duplo para lidar com diferentes tipos de interações.

## Características Principais

- **Gerenciamento de Múltiplos Números**: Capacidade de gerenciar várias contas de WhatsApp simultaneamente
- **Abordagem de Cliente Duplo**:
  - **Baileys** para interações em grupo
  - **Web.js** para mensagens diretas
- **Memória Contextual Unificada**: Mantém o contexto em todas as interações
- **Suporte a Mídia**: Manipula mensagens de texto, imagens, vídeos, documentos e áudio
- **Autenticação por QR Code**: Gerencia a autenticação de múltiplos clientes

## Inicialização Rápida

Para iniciar a integração do WhatsApp com configurações padrão:

```bash
npm run whatsapp:start
```

Este comando iniciará o script de exemplo que configura dois clientes WhatsApp (um para grupos e outro para mensagens diretas) e conecta-os ao VoxAgent.

## Uso em Código

```javascript
const VoxAgent = require('../../core/VoxAgent');
const { WhatsAppIntegration } = require('./index');

// Inicializar VoxAgent
const voxAgent = new VoxAgent();
await voxAgent.initialize(mongoConnection);

// Inicializar integração do WhatsApp
const whatsapp = new WhatsAppIntegration(voxAgent, {
  sessionsDir: './.whatsapp-sessions', // Diretório para armazenar sessões
  mediaDir: './media' // Diretório para armazenar mídia recebida
});

await whatsapp.initialize();

// Criar cliente para grupos (utilizando Baileys)
const groupClient = await whatsapp.createGroupClient('telefone-grupos');

// Criar cliente para mensagens diretas (utilizando Web.js)
const directClient = await whatsapp.createDirectClient('telefone-direto');

// Enviar mensagem
await whatsapp.sendMessage('5511999999999', 'Olá do VoxAgent!');

// Enviar mídia
await whatsapp.sendMediaMessage('5511999999999', {
  type: 'image',
  data: '/caminho/para/imagem.jpg',
  caption: 'Veja esta imagem!'
});
```

## Estrutura de Arquivos

- `WhatsAppManager.js` - Gerenciador unificado para ambos os clientes
- `integration.js` - Integração com o VoxAgent
- `example.js` - Script de exemplo de uso
- `baileys/client.js` - Cliente Baileys para interações em grupo
- `webjs/client.js` - Cliente Web.js para mensagens diretas
- `common/types.js` - Definições de tipos comuns
- `common/utils.js` - Funções utilitárias
- `index.js` - Exportações para facilitar a importação

## Autenticação

Para autenticar um cliente, execute o script de exemplo e escaneie o código QR exibido no terminal com o aplicativo WhatsApp no seu telefone.

## Próximos Passos

- Adicionar suporte para resposta automática com IA mais avançada
- Implementar análise de sentimento para mensagens recebidas
- Melhorar o rastreamento de contexto com base em tópicos de conversa
