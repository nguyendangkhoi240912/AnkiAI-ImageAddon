# AnkiAI Update Script - Usage Guide

**Script**: `update.sh`  
**Purpose**: Automate addon versioning, building, and deployment  
**Status**: Ready to use ✅

---

## 🚀 Quick Start

### Bump Patch Version and Build
```bash
./update.sh --bump-patch
```
Result: `4.4.1` → `4.4.2`, builds `AnkiAI_ImageAddon-4.4.2.ankiaddon`

### Bump Minor Version and Build
```bash
./update.sh --bump-minor
```
Result: `4.4.1` → `4.5.0`, builds `AnkiAI_ImageAddon-4.5.0.ankiaddon`

### Bump Major Version and Build
```bash
./update.sh --bump-major
```
Result: `4.4.1` → `5.0.0`, builds `AnkiAI_ImageAddon-5.0.0.ankiaddon`

### Update to Specific Version
```bash
./update.sh version 4.5.0
```

---

## 📋 All Options

```bash
./update.sh version 4.5.0              # Specific version
./update.sh --bump-patch               # Patch: 4.4.1 → 4.4.2
./update.sh --bump-minor               # Minor: 4.4.1 → 4.5.0
./update.sh --bump-major               # Major: 4.4.1 → 5.0.0
./update.sh --dry-run                  # Preview changes
./update.sh --upload                   # Show AnkiWeb upload instructions
./update.sh --github                   # Show GitHub release instructions
./update.sh --help                     # Show full help
```

---

## 🎯 Practical Examples

### Scenario 1: Quick Patch Fix
```bash
./update.sh --bump-patch
```
- Updates version automatically
- Builds new package
- Creates git commit and tag
- Ready to upload

### Scenario 2: Feature Release with GitHub
```bash
./update.sh --bump-minor --github
```
- Bumps minor version
- Builds package
- Git commit + tag
- Shows GitHub release instructions

### Scenario 3: Major Release with Preview
```bash
./update.sh --bump-major --dry-run
```
- Shows what would change
- Doesn't actually make changes
- Useful to verify before running

### Scenario 4: Manual Version Update
```bash
./update.sh version 5.0.0 --upload
```
- Sets specific version
- Builds package
- Shows AnkiWeb upload instructions

---

## 🔄 What the Script Does

### Step 1: Version Bump
- Reads current version from `manifest.json`
- Calculates new version (patch/minor/major) or uses specified version
- Validates version format (X.Y.Z)

### Step 2: Update Manifest
- Backs up `manifest.json`
- Updates `"version"` field to new version
- Confirms with success message

### Step 3: Build Addon
- Runs `python3 build.py build`
- Creates `AnkiAI_ImageAddon-X.Y.Z.ankiaddon`
- Confirms successful build

### Step 4: Git Operations
- Creates git commit with release message
- Creates git tag for version
- Pushes to repository (if configured)

### Step 5: Provide Next Steps
- Shows addon file location and size
- Displays upload instructions (if requested)
- Lists recommended next actions

---

## 📦 Output Files

After running the script, you get:

```
AnkiAI_ImageAddon/
├── manifest.json (updated with new version)
├── .git/
│   └── refs/tags/v4.5.0 (new git tag)
│
AnkiAI_ImageAddon-4.5.0.ankiaddon (new package, ready to deploy)
```

---

## 📤 Deployment After Update

### Upload to AnkiWeb
1. Go to https://ankiweb.net/
2. Log in and navigate to Add-ons
3. Find your addon and click "Update"
4. Upload the `.ankiaddon` file
5. Fill in version notes
6. Publish

### GitHub Release
1. Create release on GitHub with tag `v4.5.0`
2. Upload the `.ankiaddon` file as release asset
3. Add release notes
4. Publish

### Direct Distribution
1. Share the `.ankiaddon` file
2. Users: Tools → Add-ons → Install from file
3. Users select and restart Anki

---

## 🛡️ Safety Features

### Dry-Run Mode
```bash
./update.sh --bump-patch --dry-run
```
- Preview all changes
- No actual modifications
- Safe to test first

### Automatic Backups
- Creates backup of `manifest.json` before changes
- Git history preserved via commits/tags
- Easy rollback if needed

### Validation
- Version format validation (X.Y.Z)
- Addon file existence check
- Git repository detection

---

## 🐛 Troubleshooting

### Error: "Unknown option"
**Solution**: Check spelling. Use `--help` for valid options.

### Error: "Addon file not found"
**Solution**: Build may have failed. Check `build.py` output and fix issues.

### Error: "Not a git repository"
**Solution**: Git operations are optional. Script will skip them gracefully.

### Version not updating in build
**Solution**: Delete old `.ankiaddon` files and rebuild.

---

## 🔧 Customization

### Change Default Directory
Edit the script's `ADDON_DIR` variable to point to your addon folder.

### Add Custom Pre/Post Hooks
Add functions before/after the main build process:
```bash
pre_build() {
    echo "Running pre-build checks..."
}

post_build() {
    echo "Running post-build tests..."
}
```

### Modify Build Command
Change the `BUILD_SCRIPT` variable or add custom build logic.

---

## 📊 Typical Update Workflow

```
Day 1: Development
  └─ Code changes, git commits

Day 2: Release
  └─ ./update.sh --bump-patch --upload
  └─ Review upload instructions
  └─ Go to AnkiWeb and upload
  └─ Publish

Day 3+: Users get update
  └─ Anki shows "Update Available"
  └─ Users install new version
```

---

## 💡 Pro Tips

1. **Always use `--dry-run` first** on major updates
2. **Update documentation** after running the script
3. **Create comprehensive release notes** before publishing
4. **Test locally** before uploading to AnkiWeb
5. **Use semantic versioning**: MAJOR.MINOR.PATCH

---

## 📞 Examples in Action

### Example 1: Bug Fix Release
```bash
$ ./update.sh --bump-patch

✅ Current version: 4.4.1
✅ Target version: 4.4.2
✅ Manifest updated to v4.4.2
✅ Addon built successfully
✅ Git commit and tag created
✅ Addon file: AnkiAI_ImageAddon-4.4.2.ankiaddon (144 KB)

Next steps:
  1. Review changes: git diff HEAD~1
  2. Upload to AnkiWeb
```

### Example 2: Feature Release
```bash
$ ./update.sh --bump-minor --github

✅ Current version: 4.4.2
✅ Target version: 4.5.0
✅ Manifest updated to v4.5.0
✅ Addon built successfully
✅ Git commit and tag created
✅ Addon file: AnkiAI_ImageAddon-4.5.0.ankiaddon (145 KB)

[GitHub instructions shown...]
```

### Example 3: Dry Run
```bash
$ ./update.sh --bump-major --dry-run

[DRY RUN] Would update: manifest.json
[DRY RUN] Would build addon
[DRY RUN] Would create commit and tag
[DRY RUN] No actual changes made
```

---

## ✨ Key Benefits

✅ **Automation** - One command to update everything  
✅ **Consistency** - Version bumping always correct  
✅ **Safety** - Backups and dry-run mode  
✅ **Git Integration** - Automatic commits and tags  
✅ **Documentation** - Clear deployment instructions  
✅ **Scalability** - Reusable for all future updates  

---

## 🚀 Ready to Use

The script is ready now! Try it:

```bash
cd /Users/nguyenkhanh/Desktop/AnkiAI-ImageAddon
./update.sh --help                    # See all options
./update.sh --bump-patch --dry-run    # Preview next update
./update.sh --bump-patch              # Actually perform update
```

---

**Script Location**: `/Users/nguyenkhanh/Desktop/AnkiAI-ImageAddon/update.sh`  
**Status**: ✅ Executable and ready to use  
**Version**: 1.0
