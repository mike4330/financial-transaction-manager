-- Fix corrupted categories and subcategories created by the file_monitor.py bug
--
-- The bug was passing parameters in the wrong order:
-- 1. get_or_create_subcategory(subcategory_name, category_id) instead of (category_id, subcategory_name)
-- 2. update_transaction_category(tx_id, category_id, subcategory_id, note) instead of (tx_id, category_name, subcategory_name, note)
--
-- This created categories with numeric names and subcategories with swapped values

BEGIN TRANSACTION;

-- Mapping of corrupted to correct IDs:
-- Category mappings:
--   5181 "1" → 1 "Shopping"
--   5139 "171" → 171 "Food & Dining"
--   5147 "191" → 191 "Banking"
--   5141 "203" → 203 "Entertainment"
--   5135 "205" → 205 "Income"
--   5161 "249" → 249 "Utilities"
--
-- Subcategory mappings:
--   5187 (corrupted Online) → 1 (Online)
--   5186 (swapped Online) → 1 (Online)
--   5145 (corrupted Groceries) → 171 (Groceries)
--   5144 (swapped Groceries) → 171 (Groceries)
--   5153 (corrupted Fees) → 191 (Fees)
--   5152 (swapped Fees) → 191 (Fees)
--   5171 (corrupted ATM) → 3320 (ATM)
--   5170 (swapped ATM) → 3320 (ATM)
--   5147 (corrupted Streaming) → 245 (Streaming)
--   5146 (swapped Streaming) → 245 (Streaming)
--   5183 (corrupted Games) → 416 (Games)
--   5182 (swapped Games) → 416 (Games)
--   5141 (corrupted Salary) → 205 (Salary)
--   5140 (swapped Salary) → 205 (Salary)
--   5167 (corrupted Electric) → 249 (Electric)
--   5166 (swapped Electric) → 249 (Electric)

-- Fix transactions with corrupted categories and subcategories

-- Shopping (cat 1, sub Online)
UPDATE transactions SET category_id = 1, subcategory_id = 1
WHERE category_id = 5181 OR subcategory_id IN (5187, 5186);

-- Food & Dining (cat 171, sub Groceries)
UPDATE transactions SET category_id = 171, subcategory_id = 171
WHERE category_id = 5139 OR subcategory_id IN (5145, 5144);

-- Banking - Fees (cat 191, sub Fees)
UPDATE transactions SET category_id = 191, subcategory_id = 191
WHERE category_id = 5147 AND subcategory_id IN (5153, 5152);

-- Banking - ATM (cat 191, sub ATM)
UPDATE transactions SET category_id = 191, subcategory_id = 3320
WHERE category_id = 5147 AND subcategory_id IN (5171, 5170);

-- Handle any remaining Banking transactions that might not have matched
UPDATE transactions SET category_id = 191 WHERE category_id = 5147;

-- Entertainment - Streaming (cat 203, sub Streaming)
UPDATE transactions SET category_id = 203, subcategory_id = 245
WHERE category_id = 5141 AND subcategory_id IN (5147, 5146);

-- Entertainment - Games (cat 203, sub Games)
UPDATE transactions SET category_id = 203, subcategory_id = 416
WHERE category_id = 5141 AND subcategory_id IN (5183, 5182);

-- Handle any remaining Entertainment transactions
UPDATE transactions SET category_id = 203 WHERE category_id = 5141;

-- Income (cat 205, sub Salary)
UPDATE transactions SET category_id = 205, subcategory_id = 205
WHERE category_id = 5135 OR subcategory_id IN (5141, 5140);

-- Utilities (cat 249, sub Electric)
UPDATE transactions SET category_id = 249, subcategory_id = 249
WHERE category_id = 5161 OR subcategory_id IN (5167, 5166);

-- Delete the corrupted subcategories (both swapped and chained)
DELETE FROM subcategories WHERE id IN (
    5138,  -- Fully corrupted Stock Sale
    5140, 5141,  -- Salary (swapped and chained)
    5144, 5145,  -- Groceries (swapped and chained)
    5146, 5147,  -- Streaming (swapped and chained)
    5152, 5153,  -- Fees (swapped and chained)
    5166, 5167,  -- Electric (swapped and chained)
    5170, 5171,  -- ATM (swapped and chained)
    5182, 5183,  -- Games (swapped and chained)
    5186, 5187   -- Online (swapped and chained)
);

-- Delete the corrupted categories (numeric names)
DELETE FROM categories WHERE id IN (5181, 5139, 5147, 5141, 5135, 5161);

COMMIT;

-- Verify the fixes
SELECT '=== VERIFICATION RESULTS ===' as '';
SELECT '' as '';

SELECT 'Transactions with corrupted categories:' as status;
SELECT COUNT(*) as count FROM transactions WHERE category_id IN (5181, 5139, 5147, 5141, 5135, 5161);

SELECT 'Transactions with corrupted subcategories:' as status;
SELECT COUNT(*) as count FROM transactions WHERE subcategory_id IN (5138, 5140, 5141, 5144, 5145, 5146, 5147, 5152, 5153, 5166, 5167, 5170, 5171, 5182, 5183, 5186, 5187);

SELECT 'Categories with numeric names:' as status;
SELECT COUNT(*) as count FROM categories WHERE name GLOB '[0-9]*';

SELECT 'Subcategories with corrupted data:' as status;
SELECT COUNT(*) as count FROM subcategories WHERE name GLOB '[0-9]*' OR CAST(category_id AS TEXT) GLOB '[A-Za-z]*';

SELECT '' as '';
SELECT 'If all counts above are 0, the fix was successful!' as '';
