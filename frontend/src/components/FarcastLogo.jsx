import React from 'react'

/**
 * Official Farcast Biosciences Logo Component
 * Adheres strictly to Farcast Brand Identity Guidelines:
 * - Logo Asset: farcast_biosciences_logo.png
 * - Clearspace Rule: Enforced around logo
 * - Colors: Primary Navy (#1E2859), Secondary Purple (#B14FC4)
 */
export default function FarcastLogo({ height = 36, withContainer = true }) {
  const logoImg = (
    <img 
      src="/farcast_biosciences_logo.png" 
      alt="Farcast Biosciences" 
      style={{ 
        height: `${height}px`,
        width: 'auto',
        display: 'block',
        objectFit: 'contain'
      }} 
    />
  )

  if (withContainer) {
    return (
      <div 
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          background: '#FFFFFF',
          padding: '6px 14px',
          borderRadius: '8px',
          border: '1px solid #E2E8F0',
          boxShadow: '0 2px 6px rgba(0, 0, 0, 0.04)',
          cursor: 'pointer'
        }}
      >
        {logoImg}
      </div>
    )
  }

  return logoImg
}
