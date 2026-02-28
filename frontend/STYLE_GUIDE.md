# Youticle Web Style Guide

## 1. Brand Direction
- Tone: analytical, creator-focused, operational
- Mood: modern dashboard + editorial highlights
- Keywords: clarity, confidence, action

## 2. Design Tokens
- Primary: `--c-primary #0e5bff`
- Primary strong: `--c-primary-strong #0044d6`
- Accent mint: `--c-accent #13b88a`
- Surface: `--c-surface #ffffff`
- Surface elevated: `--c-surface-soft #eef3ff`
- Border: `--c-border #ced9f6`
- Text strong: `--c-text #101426`
- Text muted: `--c-muted #5d6888`
- Error: `--c-error #d92f3a`

## 3. Typography
- Heading font: `"Space Grotesk", "Noto Sans KR", sans-serif`
- Body font: `"SUIT Variable", "Noto Sans KR", sans-serif`
- Hero title: `clamp(2rem, 5vw, 3rem)` / `700`
- Section title: `1.1rem` / `600`
- Body: `0.98rem` / `400`
- Caption: `0.84rem` / `500`

## 4. Spacing & Radius
- Base spacing unit: `8px`
- Card padding: `24px`
- Gap base: `16px`
- Radius sm: `10px`
- Radius md: `16px`
- Radius lg: `22px`

## 5. Components
- `Card`: white surface + subtle border, optional soft gradient highlight
- `Input`: clear focus ring, no heavy shadows
- `Primary Button`: blue gradient fill, high-contrast text
- `Badge`: status chip with color-coded background

## 6. Layout Rules
- Desktop max width: `1080px`
- Content grid: `12-column feeling` using responsive card widths
- Mobile first: single-column stack under `840px`

## 7. Motion
- Use short transitions: `150ms to 220ms`
- Interactive elements should animate color and elevation only
- Avoid decorative continuous animation during data tasks

