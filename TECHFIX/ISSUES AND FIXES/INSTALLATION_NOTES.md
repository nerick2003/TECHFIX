# Installation Notes

## Optional Dependencies

The application will work without the following packages, but they provide enhanced functionality:

### Security Packages (Optional)
- **bcrypt** - Better password hashing (fallback: SHA256 with salt)
- **cryptography** - Encryption support (currently not used, but available for future features)

**Installation:**
```powershell
pip install bcrypt cryptography
```

If installation times out, try:
```powershell
pip install --default-timeout=300 bcrypt cryptography
```

Or install one at a time:
```powershell
pip install bcrypt
pip install cryptography
```

### Data Import Package (Optional)
- **pandas** - Required for Excel/CSV import feature

**Installation:**
```powershell
pip install pandas
```

If installation times out:
```powershell
pip install --default-timeout=300 pandas
```

## Network Timeout Issues

If you're experiencing timeout errors when installing packages:

1. **Increase timeout:**
   ```powershell
   pip install --default-timeout=300 <package-name>
   ```

2. **Install one package at a time** (more reliable)

3. **Use a different index** (if available):
   ```powershell
   pip install -i https://pypi.org/simple/ <package-name>
   ```

4. **Check your internet connection** - slow connections may need longer timeouts

## Running Without Optional Packages

The application will run fine without these packages:
- ✅ Authentication works with fallback password hashing
- ✅ All core features work
- ❌ Excel/CSV import will be disabled (shows error message)

## Current Status

The app is designed to work with or without these optional dependencies. All features have fallbacks or graceful degradation.

