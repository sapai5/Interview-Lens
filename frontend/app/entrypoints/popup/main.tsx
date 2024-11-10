import * as React from 'react';
import * as ReactDOM from 'react-dom/client';
import App from './App';
import '../../assets/style.css';  // Updated path

const container = document.getElementById('app');
if (!container) {
    throw new Error('Root element with id "app" not found');
}

const root = ReactDOM.createRoot(container);
root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);