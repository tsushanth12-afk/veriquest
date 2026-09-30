import type { ApiResponse } from './client';
export function requireApiData<T>(response: ApiResponse<T>): T {
  if (response.error) throw new Error(`${response.error.code}: ${response.error.message}`);
  if (response.data === null) throw new Error('SYSTEM_ERROR: Backend response is missing data.');
  return response.data;
}
