import React from 'react';

export default function Logo({
    className = "",
    useGradient = false,
    useSchemeColor = false,
    size = 100,
    variant = 'wordmark',
}) {
    const primaryColor = useSchemeColor ? "var(--secondary)" : "var(--text-main, #ffffff)";
    const secondaryColor = useSchemeColor ? "var(--secondary-glow)" : "var(--text-muted, #a1a1aa)";
    const isIcon = variant === 'icon' || className.includes('icon');

    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 200 80"
            className={className}
            width={size}
            height={size * 0.4}
        >
            {useGradient && (
                <defs>
                    <linearGradient id="logo-gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={primaryColor} />
                        <stop offset="100%" stopColor={useSchemeColor ? "var(--secondary)" : secondaryColor} />
                    </linearGradient>
                </defs>
            )}
            {isIcon ? (
                <g>
                    <rect x="60" y="0" width="80" height="80" rx="16" fill="none" stroke={useGradient ? "url(#logo-gradient)" : "currentColor"} strokeWidth="10" />
                    <text
                        x="100"
                        y="45"
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fontFamily="var(--font-heading)"
                        fontWeight="900"
                        fontSize="54"
                        fill={useGradient ? "url(#logo-gradient)" : "currentColor"}
                    >
                        R
                    </text>
                </g>
            ) : (
                <text
                    x="50%"
                    y="55%"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontFamily="var(--font-heading)"
                    fontWeight="900"
                    fontSize="68"
                    fill={useGradient ? "url(#logo-gradient)" : "currentColor"}
                    stroke={useGradient ? "url(#logo-gradient)" : "currentColor"}
                    strokeWidth="8"
                    strokeLinejoin="round"
                    letterSpacing="-0.04em"
                >
                    RAST
                </text>
            )}
        </svg>
    );
}
