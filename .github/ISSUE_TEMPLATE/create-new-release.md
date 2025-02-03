---
name: Create new release
about: Tasks for creating a new realase
title: Create new release
labels: ''
assignees: ''

---

- [ ] Ensure all other issues in the milestone have been closed or removed
- [ ] Create a new branch from main
- [ ] In the new branch, bump the version in setup.py to the new production version
- [ ] Create a new tag from the branch, named by the version
- [ ] Create a new release form the tag
- [ ] Issue a PR updating the main branch version to the new dev version (`<version>.dev`) in setup.py, closing this issue
