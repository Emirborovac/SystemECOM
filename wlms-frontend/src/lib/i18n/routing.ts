export const locales = ["en", "bs", "de"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";




