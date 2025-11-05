let ACCESS_TOKEN_MEM = ''

export const setAccessToken = (t: string) => { ACCESS_TOKEN_MEM = t || '' }
export const getAccessToken = () => ACCESS_TOKEN_MEM
export const clearAccessToken = () => { ACCESS_TOKEN_MEM = '' }