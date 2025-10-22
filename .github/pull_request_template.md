## 🎯 Pull Request Summary

**Fixes** #[issue-number]: [Brief description]

## 📝 Changes Made

<!-- Describe what was changed and why -->

## ✅ Pre-Merge Checklist

Before requesting review, verify:

- [ ] **Issue created FIRST** before work began
- [ ] **Branch naming** follows pattern: `[issue-number]-description`
- [ ] **Tests added** and passing
- [ ] **Documentation updated** (if needed)
- [ ] **No linting errors** (all pre-commit hooks passed)
- [ ] **Performance validated** (if applicable)
- [ ] **Security reviewed** (no hardcoded secrets, proper error handling)

## 🔍 Testing Performed

<!-- Describe how you tested these changes -->

- [ ] Unit tests added/updated
- [ ] Integration tests verified
- [ ] Manual testing completed

## 🎨 Screenshots (if UI changes)

<!-- Add screenshots for visual changes -->

## 📊 Performance Impact

<!-- Note any performance implications -->

## 🔒 Security Considerations

<!-- Note any security implications -->

---

## 🎉 Post-Merge Cleanup Checklist

**⚠️ IMPORTANT**: After this PR is merged, you MUST complete the following steps per constitution requirements:

### Automatic Cleanup (by GitHub Actions)
- ✅ Remote branch will be **automatically deleted** by the `branch-cleanup` workflow
- ✅ Cleanup reminder will be posted as a PR comment

### Manual Local Cleanup (REQUIRED)
- [ ] Switch to main: `git checkout main`
- [ ] Update main: `git pull origin main`
- [ ] Delete local branch: `git branch -d [branch-name]`
- [ ] Verify cleanup: `git branch -a`

**Or run the automated cleanup script**:
```bash
./.specify/scripts/bash/post-merge-cleanup.sh
```

**Constitution Reference**: Section I.IV - Issue Closure and Branch Cleanup
**Location**: `.specify/memory/constitution.md` lines 104-109, 416-422
