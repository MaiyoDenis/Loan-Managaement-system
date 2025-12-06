import { configureStore, combineReducers } from '@reduxjs/toolkit';

// Placeholder reducer for now
const placeholderReducer = (state = {}, action: any) => state;

// Combine reducers (add more as needed)
const rootReducer = combineReducers({
  placeholder: placeholderReducer,
});

export const store = configureStore({
  reducer: rootReducer,
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
