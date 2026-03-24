import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
    return useContext(ThemeContext);
}

export function ThemeProvider({ children }) {
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem('app-theme') || 'dark';
    });

    const [colorScheme, setColorScheme] = useState(() => {
        return localStorage.getItem('app-color-scheme') || 'default';
    });

    useEffect(() => {
        localStorage.setItem('app-theme', theme);
        document.documentElement.setAttribute('data-theme', theme);
    }, [theme]);

    useEffect(() => {
        localStorage.setItem('app-color-scheme', colorScheme);
        document.documentElement.setAttribute('data-color', colorScheme);
    }, [colorScheme]);

    const value = {
        theme,
        setTheme,
        colorScheme,
        setColorScheme
    };

    return (
        <ThemeContext.Provider value={value}>
            {children}
        </ThemeContext.Provider>
    );
}
