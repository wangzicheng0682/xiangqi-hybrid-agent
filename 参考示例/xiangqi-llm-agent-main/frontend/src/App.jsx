import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import GamePage from './pages/GamePage';
import ReplayPage from './pages/ReplayPage';
import ELOPage from './pages/ELOPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <Link to="/" className="nav-logo">
              中国象棋AI
            </Link>
            <div className="nav-links">
              <Link to="/game">实时对弈</Link>
              <Link to="/replay">对弈回放</Link>
              <Link to="/elo">ELO曲线</Link>
            </div>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<GamePage />} />
          <Route path="/game" element={<GamePage />} />
          <Route path="/replay" element={<ReplayPage />} />
          <Route path="/elo" element={<ELOPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

