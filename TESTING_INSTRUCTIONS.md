# Testing Instructions for Order Editing Features

## Fixed Issues
✅ Vehicle ID and Rider ID now display correctly from database
✅ Order Line Items editing and saving
✅ Order Transactions editing and saving
✅ JavaScript errors resolved

## How to Test Order Line Items Editing

### Step 1: Navigate to an Order
1. Go to the dashboard
2. Click on any order to view its details
3. Look for the "Order Items" section

### Step 2: Enable Edit Mode for Line Items
1. In the "Order Items" section, look for the card header
2. Click the "Edit Items" button (this should enable edit mode)
3. You should see:
   - Input fields become visible for each item
   - The table headers and cells become editable
   - A "Save Items" button appears

### Step 3: Edit Item Data
You can edit the following fields for each item:
- **SKU ID**: The product identifier
- **Product Name**: The name of the product
- **Description**: Product description
- **Quantity**: Number of items (use numbers only)
- **Weight**: Weight per unit (use decimal numbers)
- **Volume**: Volume per unit (use decimal numbers)
- **Unit**: Select from dropdown (PIECES, BOXES, etc.)
- **Handling Unit**: Text field for handling unit

### Step 4: Save Changes
1. After making your edits, click the "Save Items" button
2. You should see a success message: "Order items updated"
3. The page will reload automatically after 1.5 seconds
4. Verify your changes are persisted by checking the displayed values

### Expected Results:
- ✅ Changes should be saved to the database
- ✅ After page reload, updated data should be visible
- ✅ No JavaScript errors in browser console
- ✅ Success message should appear

## How to Test Order Transactions Editing

### Step 1: Navigate to Order with Transaction Data
1. Go to an order detail page that has transaction data
2. Look for the "Transaction Details" section
3. This section shows transaction status for each line item

### Step 2: Enable Edit Mode for Transactions
1. In the "Transaction Details" section, click "Edit Transactions"
2. You should see input fields become editable for:
   - **Ordered Quantity**: Number ordered
   - **Transacted Quantity**: Number actually delivered/processed
   - **Transacted Weight**: Weight of delivered items
   - **Status**: Dropdown with options (DELIVERED, PARTIALLY_DELIVERED, NOT_DELIVERED, RETURNED)

### Step 3: Edit Transaction Data
1. Modify any of the editable fields
2. For quantities and weights, use numeric values
3. For status, select from the dropdown options

### Step 4: Save Transaction Changes
1. Click the "Save Transactions" button
2. You should see a success message
3. The page should update to show your changes
4. Verify the data persists after page refresh

### Expected Results:
- ✅ Transaction data should be saved successfully
- ✅ Updated values should be visible immediately
- ✅ No "orderId is not defined" errors
- ✅ Data should persist after page reload

## Troubleshooting

### If Order Items Don't Save:
1. Check browser console for JavaScript errors
2. Verify the order has line items data
3. Ensure you're editing valid data (numbers for quantities, etc.)
4. Check that the "propagateToOrders" option is working

### If Transactions Don't Save:
1. Verify the order has transaction data in orderMetadata
2. Check that transaction IDs match line item IDs
3. Ensure numeric fields contain valid numbers
4. Check browser network tab for API call responses

### If Data Doesn't Persist:
1. Verify the order exists in the database
2. Check that raw_data field is being updated
3. Ensure the page reload is fetching updated data from database
4. Look for logging messages in the application logs

## Test Data Verification

### Database Verification:
```sql
-- Check order raw_data for updated line items
SELECT raw_data FROM orders WHERE id = 'YOUR_ORDER_ID';

-- Look for orderMetadata.lineItems and orderMetadata.transactions in the JSON
```

### Log Verification:
Look for these log messages:
- `INFO:app.editing_routes:Received line items data: [...]`
- `INFO:app.editing_routes:Processing item: {...}`
- `INFO:app.editing_routes:Updated line items for order ORDER_ID`
- `INFO:app.routes:Using X line items from database for order ORDER_ID`

## Known Limitations

1. **API Data Precedence**: If external API data is fresher than database, it may override saved changes. The system now prioritizes database data when available.

2. **Transaction Structure**: Transactions are stored within line items' transactionStatus field, not as separate entities.

3. **Field Validation**: Basic validation is in place, but complex business rules may need additional validation.

## Success Criteria

✅ **Order Line Items**:
- Edit mode toggles correctly
- All fields are editable
- Data saves successfully
- Changes persist after page reload
- No JavaScript errors

✅ **Order Transactions**:
- Edit mode toggles correctly
- Transaction fields are editable
- Save functionality works without errors
- Data persists correctly
- Status updates work properly

✅ **General**:
- Vehicle ID and Rider ID display correct values
- No "orderId is not defined" errors
- All AJAX calls complete successfully
- Database updates are reflected in UI