# Frontend TypeScript Build Errors Fix

## Critical Issues
- [ ] Replace 'react-query' imports with '@tanstack/react-query'
- [ ] Fix MUI Grid component usage (item prop issues)
- [ ] Add missing isLoading property to AuthContextType
- [ ] Add missing exports in api.ts (paymentsAPI, mpesaAPI)

## Unused Variables/Imports
- [ ] Remove unused React import in App.tsx
- [ ] Remove unused setLoading in AuthContext.tsx
- [ ] Remove unused imports in various pages (Alert, DownloadIcon, etc.)
- [ ] Remove unused variables (selectedAccount, savingsLoading, etc.)
- [ ] Remove unused AxiosResponse import in api.ts
- [ ] Remove unused action parameter in store.ts

## Type Issues
- [ ] Fix implicit any types in PaymentsPage.tsx
- [ ] Fix Grid component prop issues across all pages

## Files to Fix
- [ ] src/App.tsx
- [ ] src/contexts/AuthContext.tsx
- [ ] src/contexts/AuthContextTypes.ts
- [ ] src/pages/accounts/AccountsPage.tsx
- [ ] src/pages/loans/LoanProductsPage.tsx
- [ ] src/pages/payments/PaymentsPage.tsx
- [ ] src/pages/users/UsersPage.tsx
- [ ] src/services/api.ts
- [ ] src/store.ts
