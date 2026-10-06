/**
 * Small helper to resolve the default image model given a flux provider and optional override.
 * Kept lightweight so unit tests can import it without pulling the full API surface.
 */
export function resolveDefaultImageModel(fluxProviderInput?: string, defaultImageModelInput?: string) {
  const fp = (fluxProviderInput || '').toLowerCase();
  const explicit = (defaultImageModelInput || '').trim();
  if (explicit) return explicit;
  return (fp === 'foundry' || fp === 'bfl') ? 'flux-pro' : 'gpt-image-1';
}
