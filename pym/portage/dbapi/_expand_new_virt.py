# Copyright 2011 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import portage
from portage.dep import Atom, _get_useflag_re

def expand_new_virt(vardb, atom):
	"""
	Iterate over the recursively expanded RDEPEND atoms of
	a new-style virtual. If atom is not a new-style virtual
	or it does not match an installed package then it is
	yielded without any expansion.
	"""
	if not isinstance(atom, Atom):
		atom = Atom(atom)
	traversed = set()
	stack = [atom]

	while stack:
		atom = stack.pop()
		if atom.blocker or \
			not atom.cp.startswith("virtual/"):
			yield atom
			continue

		matches = vardb.match(atom)
		if not (matches and matches[-1].startswith("virtual/")):
			yield atom
			continue

		virt_cpv = matches[-1]
		if virt_cpv in traversed:
			continue

		traversed.add(virt_cpv)
		eapi, iuse, rdepend, use = vardb.aux_get(virt_cpv,
			["EAPI", "IUSE", "RDEPEND", "USE"])
		if not portage.eapi_is_supported(eapi):
			yield atom
			continue

		# Validate IUSE and IUSE, for early detection of vardb corruption.
		useflag_re = _get_useflag_re(eapi)
		valid_iuse = []
		for x in iuse.split():
			if x[:1] in ("+", "-"):
				x = x[1:]
			if useflag_re.match(x) is not None:
				valid_iuse.append(x)
		valid_iuse = frozenset(valid_iuse)

		iuse_implicit_match = vardb.settings._iuse_implicit_match
		valid_use = []
		for x in use.split():
			if x in valid_iuse or iuse_implicit_match(x):
				valid_use.append(x)
		valid_use = frozenset(valid_use)

		success, atoms = portage.dep_check(rdepend,
			None, vardb.settings, myuse=valid_use,
			myroot=vardb.root, trees={vardb.root:{"porttree":vardb.vartree,
			"vartree":vardb.vartree}})

		if success:
			stack.extend(atoms)
		else:
			yield atom