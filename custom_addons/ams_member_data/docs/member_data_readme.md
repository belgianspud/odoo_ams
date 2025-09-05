# AMS Member Data Module

## Overview

The AMS Member Data module is the foundational data layer for the Association Management System (AMS). It extends Odoo's native contact management with association-specific member and organization data structures.

## Features

### Individual Members
- Enhanced name components (first, middle, last, suffix, nickname)
- Demographics tracking (gender, date of birth)
- Multiple contact methods (business phone, mobile phone, secondary email)
- Dual address management (primary and secondary addresses)
- Auto-generated unique member IDs

### Organization Members
- Corporate identity fields (acronym, website, tax IDs)
- Business details (organization type, industry, employee count)
- Portal management and employee relationships
- Revenue and business metrics tracking

### Data Quality
- Phone number formatting and validation
- Email address validation
- Address standardization
- Legacy system integration support

## Installation

1. Install via Odoo Apps interface or command line:
   ```bash
   ./odoo-bin -d <database> -i ams_member_data