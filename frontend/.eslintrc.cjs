/* POLIS frontend lint — Implementation Plan task 1.8. */
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['@typescript-eslint', 'react', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  settings: { react: { version: 'detect' } },
  ignorePatterns: ['dist', 'node_modules'],
  rules: {
    // SEC-13: ingested source text is untrusted. React escapes text nodes by
    // default; dangerouslySetInnerHTML would bypass that. Banned repo-wide,
    // enforced here so a violation fails CI rather than review.
    'react/no-danger': 'error',
    'react/react-in-jsx-scope': 'off',
  },
};
