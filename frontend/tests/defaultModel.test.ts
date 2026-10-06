import { describe, it, expect } from 'vitest';
import { resolveDefaultImageModel } from '../services/defaultModel';

describe('resolveDefaultImageModel', () => {
  it('returns flux-pro when provider is foundry and no explicit default provided', () => {
    expect(resolveDefaultImageModel('foundry', '')).toBe('flux-pro');
  });

  it('returns flux-pro when provider is bfl and no explicit default provided', () => {
    expect(resolveDefaultImageModel('bfl', '')).toBe('flux-pro');
  });

  it('returns explicit default when provided', () => {
    expect(resolveDefaultImageModel('foundry', 'gpt-image-1')).toBe('gpt-image-1');
  });

  it('returns gpt-image-1 when no provider and no explicit default', () => {
    expect(resolveDefaultImageModel('', '')).toBe('gpt-image-1');
  });
});
