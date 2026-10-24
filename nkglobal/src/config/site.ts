/** Único número de WhatsApp oficial do site. Altere apenas aqui. */
export const WHATSAPP_NUMBER = '5511978714365';
export const WHATSAPP_DISPLAY = '(11) 97871-4365';

export const WHATSAPP_MESSAGES = {
  contact: 'Olá! Gostaria de falar com um atendente da NK Global.',
  quote: 'Olá! Gostaria de solicitar um orçamento.',
  info: 'Olá! Gostaria de mais informações.',
  diagnostic: 'Olá! Gostaria de solicitar um diagnóstico.',
} as const;

export function whatsappLink(message: string = WHATSAPP_MESSAGES.contact): string {
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
}

export function openWhatsApp(message: string): void {
  const url = whatsappLink(message);
  const win = window.open(url, '_blank');
  if (win) win.opener = null;
  else window.location.href = url;
}

export interface LeadData { nome: string; telefone: string; email: string }

/** Mensagem enviada ao WhatsApp da empresa a partir do pop-up/formulários. */
export function diagnosticMessage({ nome, telefone, email }: LeadData): string {
  const phone = telefone.replace(/\D/g, '');
  return `Olá, meu nome é ${nome.trim().toUpperCase()}. Gostaria de solicitar um diagnóstico estratégico de operações e alta performance, com foco em excelência e evolução dos processos. Contato: Telefone: ${phone} E-mail: ${email.trim()}`;
}

export const SITE = {
  name: 'NK Global Services',
  shortName: 'NK GLOBAL',
  tagline:
    'Excelência em negócios e governança para ativos de alto padrão. Redefinindo o conceito de facilities management.',
  cnpj: '54.246.086/0001-66',
  email: 'contato@nkglobal.com.br',
  address: ['Av Presidente Juscelino Kubitschek, 1327', '4º andar, Conjunto 41, Sala 1401', 'São Paulo, SP'],
  copyright: '© 2026 NK GLOBAL Services. Todos os direitos reservados.',
};

/** Rota no Google Maps até o escritório; sem origem definida, o Maps usa a localização de quem clicou. */
export const MAPS_DIRECTIONS_URL = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(SITE.address.join(', '))}`;

export const NAV = [
  { label: 'Página Principal', href: '/' },
  { label: 'Quem Somos', href: '/quem-somos' },
  { label: 'Serviços', href: '/servicos' },
  { label: 'Diferenciais', href: '/diferenciais' },
] as const;

/** Os PDFs mostram os ícones, mas não os endereços. Preencha as URLs quando disponíveis; sem URL o ícone não é exibido. */
export const SOCIAL = [
  { label: 'LinkedIn', icon: 'linkedin', href: '' },
  { label: 'Instagram', icon: 'instagram', href: '' },
] as const;

/** Páginas de Privacidade/Termos não foram fornecidas; sem href aparecem apenas como texto. */
export const LEGAL = [
  { label: 'Privacidade', href: '' },
  { label: 'Termos', href: '' },
] as const;
