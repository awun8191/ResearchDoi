import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
    return useContext(ThemeContext);
}

export function ThemeProvider({ children }) {
    const [colorScheme, setColorScheme] = useState(() => {
        return localStorage.getItem('app-color-scheme') || 'default';
    });

    useEffect(() => {
        localStorage.setItem('app-color-scheme', colorScheme);
        document.documentElement.setAttribute('data-color', colorScheme);
        // Force dark theme attribute as well for any legacy CSS
        document.documentElement.setAttribute('data-theme', 'dark');
    }, [colorScheme]);

    const value = {
        colorScheme,
        setColorScheme
    };

    return (
        <ThemeContext.Provider value={value}>
            {children}
        </ThemeContext.Provider>
    );
}
