# Migration Notes

## Version 1.0.0 - Module Consolidation

### Changes from Previous Versions

This version consolidates the `ams_foundation` and `membership_community` modules into a single unified module.

### Breaking Changes

1. **Membership Type Model Change**
   - **Removed**: `membership.type` (simple membership types)
   - **Now Using**: `ams.member.type` (advanced membership types)
   
2. **If Upgrading from Old membership_community**:
   - Any existing `membership.type` records need to be manually migrated
   - Create equivalent `ams.member.type` records
   - Update `membership.membership` records to link to new member types

### Data Migration Steps

If you have existing data in the old `membership.type` model:

1. Export existing membership types
2. Create equivalent records in `ams.member.type` with mapping:
   - `name` → `name`
   - `price` → `base_annual_fee`
   - `duration_type` → configure `membership_period_type` accordingly
   - `duration_months` → calculate `membership_duration` in days
   
3. Update membership records to reference new member types
4. Verify all memberships have correct types assigned

### New Features Available

With the consolidation, you now have access to:
- Product class categorization (membership, chapter, newsletter, etc.)
- Pro-rating configurations
- Upgrade/downgrade rules
- Geographic and eligibility restrictions
- Advanced approval workflows
- Engagement scoring integration