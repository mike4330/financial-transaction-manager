# Recurring Patterns - Code Review TODO

## 🔴 CRITICAL - Fix Immediately

### Security & Validation
- [ ] **Input Validation** - Add validation for user inputs before API calls
  - `api_server.py:1967` - Validate confidence is a number before dividing by 100
  - `api_server.py:2042` - Add bounds checking for lookback_days (min: 30, max: 1095)
  - `RecurringPatterns.tsx:548` - Validate lookbackDays before sending to API
  - Add server-side validation for all user inputs

- [ ] **Division by Zero** - Add zero checks in category spending analysis
  - Check if periods array has data before calculating statistics
  - Handle edge case where no transactions match criteria

### Architecture
- [ ] **Hardcoded Account Number** - Make account configurable
  - `api_server.py:2212` - Accept account_number as parameter (default: 'Z06431462')
  - `RecurringPatterns.tsx:414` - Load account from user settings/context
  - Allow users to select account for projections

---

## 🟡 HIGH PRIORITY - Fix Soon

### Error Handling
- [ ] **Silent Failures** - Improve error reporting to users
  - `RecurringPatterns.tsx:353` - Show user-friendly error for category load failure
  - `RecurringPatterns.tsx:164-209` - Report individual pattern save failures clearly
  - Consider batch API operation instead of individual saves in loop

- [ ] **Standardize Error Handling** - Use consistent pattern throughout
  - Create utility function for error handling
  - Always show user feedback for errors
  - Log errors properly on backend

### State Management
- [ ] **User Preferences** - Persist user settings
  - `RecurringPatterns.tsx:76` - Load startingBalance from account data
  - `RecurringPatterns.tsx:77` - Save/load projectionDays preference
  - `RecurringPatterns.tsx:75` - Save/load lookbackDays preference

### Performance
- [ ] **Memoize Expensive Calculations**
  - `RecurringPatterns.tsx:870` - Use useMemo for filtered projections
  - `RecurringPatterns.tsx:946` - Use useMemo for transaction markers
  - `RecurringPatterns.tsx:265-300` - Memoize sortedPatterns calculation

### Date Handling
- [ ] **Fix Timezone Issues** - Use proper date library
  - Install date-fns or dayjs
  - Replace manual date parsing at lines 877-880, 898-907, 1029-1038
  - Create utility functions for date formatting

### Loading States
- [ ] **Separate Loading States** - Don't block UI unnecessarily
  - Create separate loading states: `detectLoading`, `saveLoading`, `projectionLoading`
  - Allow users to navigate while background operations run
  - Show operation-specific loading indicators

---

## 🟢 MEDIUM PRIORITY - Improve Quality

### Accessibility
- [ ] **Replace Browser Dialogs**
  - `RecurringPatterns.tsx:236` - Replace confirm() with accessible modal component
  - `RecurringPatterns.tsx:195` - Replace alert() with toast notification system

- [ ] **Keyboard Accessibility**
  - `RecurringPatterns.tsx:584` - Add keyboard support to pattern cards
    - Add `role="button"`, `tabIndex={0}`, `onKeyDown` handler
  - Add focus styles for all interactive elements
  - Test full keyboard navigation

- [ ] **Focus Management**
  - `RecurringPatterns.module.css:284` - Add focus styles to sortable headers
  - Ensure tab order is logical
  - Add focus trap to modal

### TypeScript Types
- [ ] **Remove any Types** - Define proper interfaces
  - `RecurringPatterns.tsx:103` - Create CategoryStats interface
  - `RecurringPatterns.tsx:266` - Type aValue and bValue properly (string | number | Date)
  - `RecurringPatterns.tsx:967` - Type shape function props

### Code Organization
- [ ] **Extract Constants** - Remove magic numbers
  - `RecurringPatterns.tsx:414` - Extract account number to config constant
  - `RecurringPatterns.tsx:422` - Document confidence calculation formula
  - `RecurringPatterns.tsx:948` - Extract filter threshold (50) to named constant
  - `RecurringPatterns.tsx:870` - Extract sampling rate to constant

### API Standardization
- [ ] **Standardize Response Formats**
  - All endpoints should return consistent structure: `{success, data, error?}`
  - Document API response formats
  - Update frontend to handle consistent format

### Backend Improvements
- [ ] **Add Rate Limiting**
  - Add rate limit to `/api/recurring-patterns/detect` (expensive operation)
  - Add rate limit to `/api/balance-projection`
  - Consider caching for frequently accessed patterns

---

## 🔵 LOW PRIORITY - Polish & Refactor

### Component Refactoring
- [x] **Break Up Large Component** - Split RecurringPatterns.tsx (~~1258~~ → ~~916~~ → 725 lines)
  - [x] Extract `DetectPatternsView` component ✅ (266 lines, completed 2026-01-11)
  - [ ] Extract `SavedPatternsView` component
  - [x] Extract `BalanceProjectionView` component ✅ (362 lines, completed 2026-01-11)
  - [ ] Extract `EstimatedPatternModal` component
  - [ ] Extract `PatternCard` component (reusable in DetectPatternsView)
  - [ ] Extract `PatternTable` component

### CSS Improvements
- [ ] **Reduce CSS Repetition**
  - Create base button class (`.btn-base`)
  - Extend for variants (`.btn-primary`, `.btn-danger`, etc.)
  - Create utility classes for common patterns

- [ ] **Remove Unused CSS**
  - `RecurringPatterns.module.css:862-871` - Remove unused `.chart-tooltip` class
  - Audit for other unused styles

### Code Quality
- [ ] **Remove Debug Code**
  - `RecurringPatterns.tsx:377` - Remove console.log or replace with proper logger

- [ ] **Add Display Names**
  - Add `RecurringPatterns.displayName = 'RecurringPatterns'`
  - Add display names to all extracted components

- [ ] **Improve Function Names**
  - `RecurringPatterns.tsx:485` - Consider renaming parameter to `withVariance`
  - `RecurringPatterns.tsx:477` - Consider more descriptive name

### Documentation
- [ ] **Add JSDoc Comments**
  - Document all major functions
  - Document API endpoints
  - Add usage examples for complex functions

- [ ] **Pattern Type Display**
  - Show pattern type ('estimated' vs 'detected') more prominently in UI
  - Add filter by pattern type

---

## 📊 Testing TODO

- [ ] **Unit Tests**
  - Test date parsing functions
  - Test currency formatting
  - Test sorting logic
  - Test pattern selection logic

- [ ] **Integration Tests**
  - Test full pattern detection flow
  - Test pattern save flow
  - Test projection calculation

- [ ] **Accessibility Tests**
  - Run axe-core or similar tool
  - Test keyboard navigation
  - Test screen reader compatibility

---

## 📝 Review Statistics

- **Critical Issues**: 3
- **High Priority**: 5
- **Medium Priority**: 8
- **Low Priority**: 11
- **Total Issues**: 27

---

## ✅ Positive Aspects (Keep Doing)

- ✨ Good TypeScript interface definitions
- ✨ Responsive design with mobile breakpoints
- ✨ Theme support (dark mode integration)
- ✨ Sortable tables with good UX
- ✨ Inline editing functionality
- ✨ Comprehensive chart visualization
- ✨ Good separation of concerns between views
- ✨ Proper use of parameterized SQL queries

---

## 🚀 Suggested Implementation Order

### Week 1: Security & Critical Fixes
1. Input validation (all forms and API endpoints)
2. Fix hardcoded account numbers
3. Add zero-division checks
4. Standardize error handling

### Week 2: Performance & UX
1. Add useMemo for expensive calculations
2. Separate loading states
3. Replace alert/confirm with better UI
4. Improve date handling with library

### Week 3: Accessibility & Types
1. Add keyboard support
2. Replace any types with proper interfaces
3. Add focus management
4. Improve error messages

### Week 4: Refactoring & Polish
1. Break component into smaller pieces
2. Extract constants and magic numbers
3. Standardize API responses
4. Clean up CSS

---

## 📞 Need Clarification

- [ ] Should balance projection support multiple accounts?
- [ ] What's the expected behavior when no patterns exist?
- [ ] Should pattern detection be a background job for large datasets?
- [ ] Are there plans for pattern matching confidence tuning by user?

---

## 📈 Refactoring Progress

### Completed 2026-01-11
- ✅ **Extracted BalanceProjectionView** (362 lines)
  - Self-contained balance projection with chart visualization
  - Reduced main component from 1258 → 916 lines
- ✅ **Extracted DetectPatternsView** (266 lines)
  - Self-contained pattern detection and selection UI
  - Reduced main component from 916 → 725 lines
- ✅ **Total reduction: 42%** (533 lines removed from main component)
- ✅ **Build verified** - No TypeScript errors

### Impact
- **Maintainability**: Smaller, focused components (725 vs 1258 lines)
- **Testability**: Each view can be tested independently
- **Parallel Development**: Multiple developers can work on different views
- **Code Organization**: Clear separation of concerns

---

*Generated: 2026-01-11*
*Updated: 2026-01-11 (Refactoring session)*
*Files Reviewed: RecurringPatterns.tsx (1258 lines), RecurringPatterns.module.css (1456 lines), api_server.py (patterns endpoints)*
