import os
from unittest import mock

from wif import refs
from .base import WifCase


class RefsTests(WifCase):
    def r(self, repos=(), prs=(), scope="justgames"):
        return refs.Resolver(scope, list(repos), list(prs))

    def test_mode_precedence_and_validation(self):
        self.assertEqual(refs.mode_from([], {}), "plain")
        self.assertEqual(refs.mode_from([], {"WIF_REFS": "md"}), "md")
        self.assertEqual(refs.mode_from(["--refs", "plain"], {"WIF_REFS": "md"}), "plain")   # flag beats env
        with self.assertRaises(ValueError): refs.mode_from(["--refs", "html"], {})
        with self.assertRaises(ValueError): refs.mode_from(["--refs"], {"WIF_REFS": "nope"})

    def test_slug_of_origin(self):
        for o in ("git@github.com:SentientDogs/flip-oracle.git", "https://github.com/SentientDogs/flip-oracle",
                  "https://github.com/SentientDogs/flip-oracle.git/", "ssh://git@github.com/SentientDogs/flip-oracle"):
            self.assertEqual(refs.slug_of_origin(o), "SentientDogs/flip-oracle", o)
        self.assertIsNone(refs.slug_of_origin("git@gitlab.com:o/r.git")); self.assertIsNone(refs.slug_of_origin(None))

    def test_pr_resolution_order(self):
        cache = [{"number": 1669, "url": "https://github.com/SentientDogs/flip-oracle/pull/1669", "repo": "flip-oracle"}]
        multi = [{"origin": "git@github.com:SentientDogs/flip-oracle.git"}, {"origin": "git@github.com:SentientDogs/flip-deploy.git"}]
        r = self.r(multi, cache)
        self.assertEqual(r.pr_url(1669), "https://github.com/SentientDogs/flip-oracle/pull/1669")   # 1. cache
        self.assertIsNone(r.pr_url(42))                                                              # 3. ambiguous -> plain
        self.assertEqual(r.pr_url(42, "x/y"), "https://github.com/x/y/pull/42")                      # explicit slug always
        single = self.r([{"origin": "https://github.com/x/y"}, {"origin": None}])
        self.assertEqual(single.pr_url(42), "https://github.com/x/y/pull/42")                        # 2. single origin
        self.assertIsNone(self.r([{"origin": "git@gitlab.com:o/r.git"}]).pr_url(1))                  # non-GitHub -> plain

    def test_issue_resolution_per_scope(self):
        self.assertEqual(self.r().issue_url("ENG-2654"), "https://linear.app/justgames/issue/ENG-2654")
        self.assertIsNone(self.r().issue_url("FOR-1"))                       # not this scope's team
        self.assertIsNone(self.r(scope="forestrie").issue_url("FOR-1"))      # team known, workspace not configured
        self.assertIsNone(self.r(scope="personal").issue_url("ENG-1"))
        with mock.patch.dict(os.environ, {"WIF_LINEAR_FORESTRIE": "forestrie-ws:FOR,ARB"}):
            r = self.r(scope="forestrie")
            self.assertEqual(r.issue_url("ARB-3"), "https://linear.app/forestrie-ws/issue/ARB-3")

    def test_linkify_patterns_idempotence_and_plain(self):
        r = self.r([{"origin": "git@github.com:o/r.git"}])
        t = "merge #12 and o/x#3; ENG-7 vs ARC-014; sha 1a2b3c; see [#12](https://github.com/o/r/pull/12) again"
        md = refs.linkify(t, r, "md")
        self.assertEqual(md, "merge [#12](https://github.com/o/r/pull/12) and [o/x#3](https://github.com/o/x/pull/3); "
                             "[ENG-7](https://linear.app/justgames/issue/ENG-7) vs ARC-014; sha 1a2b3c; "
                             "see [#12](https://github.com/o/r/pull/12) again")
        self.assertEqual(refs.linkify(md, r, "md"), md)                     # idempotent
        self.assertEqual(refs.linkify(t, r, "plain"), t)                     # plain: byte-identical
        self.assertEqual(refs.linkify("", r, "md"), ""); self.assertEqual(refs.linkify(None, r, "md"), "")
        self.assertEqual(refs.linkify("cut #16… and ENG-2… but #16 and ENG-2 ok", r, "md"),           # a trimmed reference is a prefix of another id: never linked
                         "cut #16… and ENG-2… but [#16](https://github.com/o/r/pull/16) and [ENG-2](https://linear.app/justgames/issue/ENG-2) ok")
        self.assertEqual(refs.linkify("fragment https://x/y#12 and C#", r, "md"), "fragment https://x/y#12 and C#")   # not after a word char / slash
