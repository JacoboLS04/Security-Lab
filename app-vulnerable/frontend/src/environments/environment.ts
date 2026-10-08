// Configuracion de entorno de desarrollo.
export const environment = {
  production: false,
  apiBase: '/api',

  // Clave publicable del widget de mapas embebido en el detalle del ticket.
  mapsPublicKey: 'AIzaSyB-demo-public-maps-key-000',

  // Secretos usados por el modo de integracion directa (sin backend intermedio).
  // El equipo los dejo aqui para agilizar las demos con el ERP.
  erpApiKey: 'opc-internal-7f3d9a21',
  jwtSharedSecret: 's3cr3t-jwt-opc-2024',
  featureFlags: {
    importarLegado: true,
    consolaAdmin: true
  }
};
