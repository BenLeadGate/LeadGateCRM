# LeadGate + GateLink — Apple-Inspired Design System
**Version 1.0**  
**Single Source of Truth for UI / UX**

---

## 1. Design Philosophy

- **Reduce visual noise.** Prefer whitespace over borders.
- **Use hierarchy via typography and spacing**, not colors.
- **One primary accent color only.**
- **Motion is subtle feedback**, never decoration.
- **Hide complexity** until the user needs it.
- **UI should feel calm, premium, and predictable.**

---

## 2. Design Tokens

### Colors

**Primary Palette:**
- Primary: `#0071e3`
- Text Primary: `#1d1d1f`
- Text Muted: `#6b7280`
- Background: `#fafafa`
- Surface: `#ffffff`
- Border: `#e5e7eb`

**Semantic Colors:**
- Success: `#16a34a`
- Warning: `#f59e0b`
- Danger: `#dc2626`

### Typography

**Font Stack:**
```
-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif
```

**Font Sizes:**
- **Page Title**: 48–56px, font-weight 600, tracking-tight
- **Section Title**: 18–20px, font-weight 600
- **Body**: 16px, font-weight 400
- **Meta**: 14px, color muted
- **Small**: 12px, color muted

### Border Radius

- **Card**: 24px (`rounded-2xl`)
- **Input / Button**: 16px (`rounded-xl`)
- **Pill / Badge**: 999px (`rounded-full`)

### Shadows

- **Cards**: `shadow-sm` or `shadow-md` only
- **No heavy shadows allowed**

### Blur

**Sticky navigation and modals:**
- `backdrop-blur-xl` or `backdrop-blur-sm`

---

## 3. Global Layout Rules

- **Max content width**: 1200px
- **Horizontal padding**: 16px mobile, 32px desktop
- **Section spacing**: 24–40px
- **Cards are the primary container**
- **Avoid full-width tables** unless necessary

---

## 4. Navigation

- **Sticky top navigation**
- **Semi-transparent background** with blur
- **Rounded navigation items**
- **Active state**: light gray background
- **Primary CTA on the right side** only

**Implementation:**
```html
<nav class="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-50">
  <div class="max-w-6xl mx-auto px-6">
    <!-- Navigation content -->
  </div>
</nav>
```

---

## 5. Core Components (Tailwind Patterns)

### Card

**Structure:**
- Background: white
- Border: 1px gray-200
- Radius: `rounded-2xl`
- Padding: 24–32px (`p-6` to `p-8`)
- Shadow: `shadow-sm`
- Header includes title + optional action

**Example:**
```html
<div class="bg-white rounded-2xl border border-gray-100 p-8">
  <div class="flex justify-between items-center mb-6">
    <h2 class="text-xl font-semibold text-[#1d1d1f]">Title</h2>
    <button class="px-4 py-2 text-sm font-semibold text-white bg-[#0071e3] rounded-xl">
      Action
    </button>
  </div>
  <!-- Card content -->
</div>
```

### Primary Button

**Specifications:**
- Background: `#0071e3`
- Text: white
- Radius: `rounded-xl`
- Padding: `px-5 py-3` (or `px-6 py-3`)
- Hover: opacity 90%
- Active: opacity 80%

**Example:**
```html
<button class="px-6 py-3 text-sm font-semibold text-white bg-[#0071e3] rounded-xl hover:bg-[#0071e3]/90 transition-smooth">
  Primary Action
</button>
```

### Secondary Button

**Specifications:**
- Background: `gray-100`
- Text: `#1d1d1f`
- Radius: `rounded-xl`
- Hover: `gray-200`

**Example:**
```html
<button class="px-6 py-3 text-sm font-semibold text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-smooth">
  Secondary Action
</button>
```

### Destructive Button

**Specifications:**
- Background: danger red (`#dc2626`)
- Text: white
- **Use sparingly**

**Example:**
```html
<button class="px-6 py-3 text-sm font-semibold text-white bg-red-600 rounded-xl hover:bg-red-700 transition-smooth">
  Delete
</button>
```

### Input

**Specifications:**
- Background: white
- Border: `gray-200`
- Radius: `rounded-xl`
- Padding: `px-4 py-3`
- Focus: blue ring (2px), no outline
- Placeholder text muted

**Example:**
```html
<input 
  type="text" 
  class="w-full px-4 py-3 border border-gray-200 rounded-xl bg-white text-[#1d1d1f] focus:outline-none focus:ring-2 focus:ring-[#0071e3] focus:border-transparent transition-smooth"
  placeholder="Placeholder text"
>
```

### Badges

**Specifications:**
- `rounded-full`
- Small font (12px)
- Soft background color
- **Never use pure saturated colors**

**Example:**
```html
<span class="px-3 py-1 text-xs font-medium rounded-full bg-green-100 text-green-700">
  Active
</span>
```

### Tables

**Specifications:**
- **No hard borders**
- Header with light gray background
- Rows separated by very light dividers
- Row hover: subtle gray background

**Example:**
```html
<table class="min-w-full">
  <thead>
    <tr class="border-b border-gray-200">
      <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Header</th>
    </tr>
  </thead>
  <tbody class="divide-y divide-gray-100">
    <tr class="hover:bg-gray-50 transition-smooth">
      <td class="px-4 py-3 text-sm text-[#1d1d1f]">Content</td>
    </tr>
  </tbody>
</table>
```

### Modals

**Specifications:**
- Backdrop: black 40% opacity + blur
- Container: white, `rounded-2xl`
- Shadow: `shadow-2xl`
- Entrance animation: fade + scale

**Example:**
```html
<div class="fixed inset-0 bg-black/40 backdrop-blur-sm overflow-y-auto h-full w-full z-50">
  <div class="relative top-20 mx-auto p-0 w-full max-w-md">
    <div class="bg-white rounded-2xl overflow-hidden shadow-2xl">
      <!-- Modal content -->
    </div>
  </div>
</div>
```

---

## 6. Motion & Interaction

**Rules:**
- **Transition duration**: 150–250ms
- **Easing**: `ease-out`
- **Hover feedback** on all interactive elements
- **Active state**: subtle scale (0.99)
- **Avoid bounce or spring animations**

**Implementation:**
```css
.transition-smooth {
  transition: all 0.2s ease-out;
}
```

**Hover Example:**
```html
<button class="hover:bg-gray-200 transition-smooth active:scale-[0.99]">
  Interactive Element
</button>
```

---

## 7. Copy & Microtext Rules

**Guidelines:**
- **Use human language**, not technical wording
- **Avoid system jargon** where possible
- **Prefer calm, neutral phrasing**

**Examples:**

| ❌ Technical | ✅ Human |
|------------|---------|
| "Rechnung erstellen" | "Abrechnung vorbereiten" |
| "Lead storniert" | "Dieser Lead wird nicht weiterverfolgt" |
| "Speichern" | "Änderungen sichern" |
| "Fehler beim Laden" | "Daten konnten nicht geladen werden" |
| "Löschen" | "Entfernen" (wenn möglich) |

---

## 8. Dashboard Design Rules

**Principles:**
- **Show insights**, not raw data
- **One key number per card**
- **Short explanatory subtitle**
- **Avoid cluttered charts**
- **Emphasize trends** over exact values

**Card Structure:**
```html
<div class="bg-white rounded-2xl p-8 border border-gray-100">
  <p class="text-sm font-medium text-gray-600 mb-2">Label</p>
  <p class="text-4xl font-semibold text-[#1d1d1f]" id="stat-value">-</p>
  <p class="text-sm text-gray-500 mt-2" id="stat-subtitle">Subtitle</p>
</div>
```

---

## 9. LeadGate vs GateLink UI Difference

### LeadGate (Internal Admin Interface)

**Characteristics:**
- **Dense information layout**
- **Tables and sidebars allowed**
- **Fast access to actions**
- **Admin-style interface**
- More data visible at once
- Compact spacing acceptable

**Use Cases:**
- Dashboard with multiple statistics
- Data tables with many columns
- Sidebar navigation
- Quick action buttons

### GateLink (External Makler Portal)

**Characteristics:**
- **Simpler screens**
- **Larger buttons and inputs**
- **Fewer actions per screen**
- **Guided, user-friendly tone**
- More whitespace
- Clearer hierarchy

**Use Cases:**
- Lead overview with large cards
- Simple forms with clear labels
- Step-by-step workflows
- Minimal navigation

---

## 10. Consistency Rules

**Mandatory:**
- ✅ **No new colors** without updating tokens
- ✅ **No new border radius values**
- ✅ **Reuse components** everywhere
- ✅ **One primary action** per screen
- ✅ **If something looks loud, remove it**

**Review Checklist:**
- [ ] Uses only design token colors
- [ ] Uses standard border radius values
- [ ] Follows spacing guidelines
- [ ] Has appropriate hover/active states
- [ ] Uses human-friendly copy
- [ ] Maintains visual hierarchy
- [ ] Reduces visual noise

---

## 11. Implementation Examples

### Complete Card with Header
```html
<div class="bg-white rounded-2xl border border-gray-100 p-8 mb-8">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h2 class="text-2xl font-semibold text-[#1d1d1f] mb-1">Section Title</h2>
      <p class="text-gray-600">Subtitle or description</p>
    </div>
    <button class="px-6 py-3 text-sm font-semibold text-white bg-[#0071e3] rounded-xl hover:bg-[#0071e3]/90 transition-smooth">
      Primary Action
    </button>
  </div>
  <!-- Content -->
</div>
```

### Statistic Card
```html
<div class="bg-white rounded-2xl p-8 border border-gray-100">
  <p class="text-sm font-medium text-gray-600 mb-2">Aktive Makler</p>
  <p class="text-4xl font-semibold text-[#1d1d1f]" id="stat-makler">-</p>
  <p class="text-sm text-gray-500 mt-2">Dieser Monat: -</p>
</div>
```

### Form Input Group
```html
<div class="mb-6">
  <label class="block text-sm font-semibold text-[#1d1d1f] mb-2">Label</label>
  <input 
    type="text" 
    class="w-full px-4 py-3 border border-gray-200 rounded-xl bg-white text-[#1d1d1f] focus:outline-none focus:ring-2 focus:ring-[#0071e3] focus:border-transparent transition-smooth"
    placeholder="Placeholder"
  >
</div>
```

### Status Badge
```html
<span class="px-3 py-1 text-xs font-medium rounded-full bg-green-100 text-green-700">
  Aktiv
</span>
```

### Navigation Item
```html
<a href="page.html" class="px-4 py-2 text-sm font-medium text-[#1d1d1f] bg-gray-100 rounded-full transition-smooth">
  Active Page
</a>
<a href="page.html" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-[#1d1d1f] rounded-full transition-smooth">
  Other Page
</a>
```

---

## 12. Common Patterns

### Empty State
```html
<div class="bg-white rounded-2xl border border-gray-100 p-16 text-center">
  <p class="text-gray-500 font-medium mb-2">Keine Daten vorhanden</p>
  <p class="text-sm text-gray-400">Beschreibung oder Handlungsaufforderung</p>
</div>
```

### Loading State
```html
<div class="bg-white rounded-2xl border border-gray-100 p-12 text-center">
  <p class="text-gray-500">Lade Daten...</p>
</div>
```

### Error State
```html
<div class="bg-red-50 border border-red-200 rounded-xl p-4">
  <p class="text-sm text-red-600">Fehlermeldung</p>
</div>
```

### Success State
```html
<div class="bg-green-50 border border-green-200 rounded-xl p-4">
  <p class="text-sm text-green-600">Erfolgreich gespeichert</p>
</div>
```

---

## 13. Accessibility Considerations

- **Color contrast**: Ensure WCAG AA compliance (4.5:1 for normal text)
- **Focus states**: Always visible, use ring-2 with primary color
- **Keyboard navigation**: All interactive elements must be keyboard accessible
- **Screen readers**: Use semantic HTML and ARIA labels where needed
- **Touch targets**: Minimum 44x44px for mobile

---

## 14. Responsive Breakpoints

**Tailwind Defaults:**
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

**Usage:**
```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <!-- Responsive grid -->
</div>
```

---

## 15. Do's and Don'ts

### ✅ Do's

- Use whitespace generously
- Maintain consistent spacing
- Use subtle shadows only
- Keep animations minimal
- Use human-friendly language
- Show one primary action per screen
- Use design tokens consistently

### ❌ Don'ts

- Don't add new colors without updating tokens
- Don't use heavy shadows
- Don't use bounce/spring animations
- Don't use technical jargon
- Don't clutter interfaces
- Don't use multiple accent colors
- Don't create new border radius values

---

**Last Updated**: Version 1.0  
**Maintained by**: LeadGate Development Team










