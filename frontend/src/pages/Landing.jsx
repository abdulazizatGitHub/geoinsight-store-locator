import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Map, Zap, Layers, Navigation, ArrowRight } from 'lucide-react'

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="landing-container">
      {/* Background elements */}
      <div className="gradient-sphere sphere-1"></div>
      <div className="gradient-sphere sphere-2"></div>
      
      <nav className="landing-nav">
        <div className="logo-container">
          <Map className="logo-icon" />
          <h1 className="logo-text">Geo<span>Insight</span></h1>
        </div>
        <div className="nav-links">
          <a href="https://github.com" target="_blank" rel="noreferrer" className="nav-link">
            Repository
          </a>
        </div>
      </nav>

      <main className="landing-main">
        <div className="hero-content">
          <div className="badge">PostGIS Spatial Analytics</div>
          <h2 className="hero-title">
            Intelligent Location Intelligence<br/>
            <span className="hero-highlight">Powered by Real-World Data</span>
          </h2>
          <p className="hero-subtitle">
            A production-grade GIS platform utilizing PostGIS for dynamic spatial aggregation, 
            Convex Hull bounding, and OSRM-powered turn-by-turn routing across 2,000+ real-world points of interest.
          </p>
          
          <div className="hero-actions">
            <button className="btn-primary-large" onClick={() => navigate('/app')}>
              Launch Application <ArrowRight size={18} />
            </button>
          </div>
        </div>

        <div className="features-grid">
          <div className="feature-card glass-card">
            <div className="feature-icon-wrapper"><Layers className="feature-icon" /></div>
            <h3>Advanced Spatial Analytics</h3>
            <p>On-the-fly convex hull generation and nearest-first geospatial querying utilizing PostgreSQL GiST indices.</p>
          </div>
          <div className="feature-card glass-card">
            <div className="feature-icon-wrapper"><Zap className="feature-icon" /></div>
            <h3>Live Analytics Dashboard</h3>
            <p>Real-time metrics, dynamic charts, and aggregate distance calculations reacting instantly to map interactions.</p>
          </div>
          <div className="feature-card glass-card">
            <div className="feature-icon-wrapper"><Navigation className="feature-icon" /></div>
            <h3>Intelligent Routing</h3>
            <p>Integrated OSRM engine for accurate walk, bike, and driving distance matrix evaluation across actual street networks.</p>
          </div>
        </div>
      </main>
    </div>
  )
}
