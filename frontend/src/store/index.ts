import { configureStore } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import parkingSlice from './slices/parkingSlice';
import uiSlice from './slices/uiSlice';
import mapSlice from './slices/mapSlice';
import analyticsSlice from './slices/analyticsSlice';
import realtimeSlice from './slices/realtimeSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice,
    parking: parkingSlice,
    ui: uiSlice,
    map: mapSlice,
    analytics: analyticsSlice,
    realtime: realtimeSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;