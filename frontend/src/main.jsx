import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// ⚠️  MUST be imported before any react-leaflet component is rendered.
// Without this, map tiles and markers render broken with no error thrown.
import 'leaflet/dist/leaflet.css'

import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
