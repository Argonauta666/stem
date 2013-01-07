"""
Unit tests for the NetworkStatusDocumentV3 of stem.descriptor.networkstatus.
"""

from __future__ import with_statement

import datetime
import StringIO
import unittest

import stem.version

from stem.descriptor import Flag

from stem.descriptor.networkstatus import HEADER_STATUS_DOCUMENT_FIELDS, \
                                          FOOTER_STATUS_DOCUMENT_FIELDS, \
                                          DEFAULT_PARAMS, \
                                          BANDWIDTH_WEIGHT_ENTRIES, \
                                          DirectoryAuthority, \
                                          NetworkStatusDocumentV3, \
                                          parse_file

from stem.descriptor.router_status_entry import \
                                          RouterStatusEntryV3, \
                                          RouterStatusEntryMicroV3

from test.mocking import support_with, \
                         get_router_status_entry_v3, \
                         get_router_status_entry_micro_v3, \
                         get_directory_authority, \
                         get_network_status_document_v3, \
                         CRYPTO_BLOB, \
                         DOC_SIG, \
                         NETWORK_STATUS_DOCUMENT_FOOTER

class TestNetworkStatusDocument(unittest.TestCase):
  def test_minimal_consensus(self):
    """
    Parses a minimal network status document.
    """
    
    document = get_network_status_document_v3()
    
    expected_known_flags = [
      Flag.AUTHORITY, Flag.BADEXIT, Flag.EXIT,
      Flag.FAST, Flag.GUARD, Flag.HSDIR, Flag.NAMED, Flag.RUNNING,
      Flag.STABLE, Flag.UNNAMED, Flag.V2DIR, Flag.VALID]
    
    self.assertEqual((), document.routers)
    self.assertEqual(3, document.version)
    self.assertEqual(None, document.version_flavor)
    self.assertEqual(True, document.is_consensus)
    self.assertEqual(False, document.is_vote)
    self.assertEqual(False, document.is_microdescriptor)
    self.assertEqual(9, document.consensus_method)
    self.assertEqual([], document.consensus_methods)
    self.assertEqual(None, document.published)
    self.assertEqual(datetime.datetime(2012, 9, 2, 22, 0, 0), document.valid_after)
    self.assertEqual(datetime.datetime(2012, 9, 2, 22, 0, 0), document.fresh_until)
    self.assertEqual(datetime.datetime(2012, 9, 2, 22, 0, 0), document.valid_until)
    self.assertEqual(300, document.vote_delay)
    self.assertEqual(300, document.dist_delay)
    self.assertEqual([], document.client_versions)
    self.assertEqual([], document.server_versions)
    self.assertEqual(expected_known_flags, document.known_flags)
    self.assertEqual(DEFAULT_PARAMS, document.params)
    self.assertEqual((), document.directory_authorities)
    self.assertEqual({}, document.bandwidth_weights)
    self.assertEqual([DOC_SIG], document.signatures)
    self.assertEqual([], document.get_unrecognized_lines())
  
  def test_minimal_vote(self):
    """
    Parses a minimal network status document.
    """
    
    document = get_network_status_document_v3({"vote-status": "vote"})
    
    expected_known_flags = [
      Flag.AUTHORITY, Flag.BADEXIT, Flag.EXIT,
      Flag.FAST, Flag.GUARD, Flag.HSDIR, Flag.NAMED, Flag.RUNNING,
      Flag.STABLE, Flag.UNNAMED, Flag.V2DIR, Flag.VALID]
    
    self.assertEqual((), document.routers)
    self.assertEqual(3, document.version)
    self.assertEqual(False, document.is_consensus)
    self.assertEqual(True, document.is_vote)
    self.assertEqual(None, document.consensus_method)
    self.assertEqual([1, 9], document.consensus_methods)
    self.assertEqual(datetime.datetime(2012, 9, 2, 22, 0, 0), document.published)
    self.assertEqual(datetime.datetime(2012, 9, 2, 22, 0, 0), document.valid_after)
    self.assertEqual(datetime.datetime(2012, 9, 2, 22, 0, 0), document.fresh_until)
    self.assertEqual(datetime.datetime(2012, 9, 2, 22, 0, 0), document.valid_until)
    self.assertEqual(300, document.vote_delay)
    self.assertEqual(300, document.dist_delay)
    self.assertEqual([], document.client_versions)
    self.assertEqual([], document.server_versions)
    self.assertEqual(expected_known_flags, document.known_flags)
    self.assertEqual(DEFAULT_PARAMS, document.params)
    self.assertEqual((), document.directory_authorities)
    self.assertEqual({}, document.bandwidth_weights)
    self.assertEqual([DOC_SIG], document.signatures)
    self.assertEqual([], document.get_unrecognized_lines())
  
  def test_examples(self):
    """
    Run something similar to the examples in the header pydocs.
    """
    
    # makes a consensus with a couple routers, both with the same nickname
    
    entry1 = get_router_status_entry_v3({'s': "Fast"})
    entry2 = get_router_status_entry_v3({'s': "Valid"})
    content = get_network_status_document_v3(routers = (entry1, entry2), content = True)
    
    # first example: parsing via the NetworkStatusDocumentV3 constructor
    
    consensus_file = StringIO.StringIO(content)
    consensus = NetworkStatusDocumentV3(consensus_file.read())
    consensus_file.close()
    
    for router in consensus.routers:
      self.assertEqual('caerSidi', router.nickname)
    
    # second example: using parse_file
    
    with support_with(StringIO.StringIO(content)) as consensus_file:
      for router in parse_file(consensus_file):
        self.assertEqual('caerSidi', router.nickname)
  
  def test_parse_file(self):
    """
    Try parsing a document via the parse_file() function.
    """
    
    entry1 = get_router_status_entry_v3({'s': "Fast"})
    entry2 = get_router_status_entry_v3({'s': "Valid"})
    content = get_network_status_document_v3(routers = (entry1, entry2), content = True)
    
    # the document that the entries refer to should actually be the minimal
    # descriptor (ie, without the entries)
    
    expected_document = get_network_status_document_v3()
    
    descriptor_file = StringIO.StringIO(content)
    entries = list(parse_file(descriptor_file))
    
    self.assertEquals(entry1, entries[0])
    self.assertEquals(entry2, entries[1])
    self.assertEquals(expected_document, entries[0].document)
  
  def test_missing_fields(self):
    """
    Excludes mandatory fields from both a vote and consensus document.
    """
    
    for is_consensus in (True, False):
      attr = {"vote-status": "consensus"} if is_consensus else {"vote-status": "vote"}
      is_vote = not is_consensus
      
      for entries in (HEADER_STATUS_DOCUMENT_FIELDS, FOOTER_STATUS_DOCUMENT_FIELDS):
        for field, in_votes, in_consensus, is_mandatory in entries:
          if is_mandatory and ((is_consensus and in_consensus) or (is_vote and in_votes)):
            content = get_network_status_document_v3(attr, exclude = (field,), content = True)
            self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
            NetworkStatusDocumentV3(content, False)  # constructs without validation
  
  def test_unrecognized_line(self):
    """
    Includes unrecognized content in the document.
    """
    
    document = get_network_status_document_v3({"pepperjack": "is oh so tasty!"})
    self.assertEquals(["pepperjack is oh so tasty!"], document.get_unrecognized_lines())
  
  def test_misordered_fields(self):
    """
    Rearranges our descriptor fields.
    """
    
    for is_consensus in (True, False):
      attr = {"vote-status": "consensus"} if is_consensus else {"vote-status": "vote"}
      lines = get_network_status_document_v3(attr, content = True).split("\n")
      
      for index in xrange(len(lines) - 1):
        # once we reach the crypto blob we're done since swapping those won't
        # be detected
        if lines[index].startswith(CRYPTO_BLOB[1:10]): break
        
        # swaps this line with the one after it
        test_lines = list(lines)
        test_lines[index], test_lines[index + 1] = test_lines[index + 1], test_lines[index]
        
        content = "\n".join(test_lines)
        self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
        NetworkStatusDocumentV3(content, False)  # constructs without validation
  
  def test_duplicate_fields(self):
    """
    Almost all fields can only appear once. Checking that duplicates cause
    validation errors.
    """
    
    for is_consensus in (True, False):
      attr = {"vote-status": "consensus"} if is_consensus else {"vote-status": "vote"}
      lines = get_network_status_document_v3(attr, content = True).split("\n")
      
      for index, line in enumerate(lines):
        # Stop when we hit the 'directory-signature' for a couple reasons...
        # - that is the one field that can validly appear multiple times
        # - after it is a crypto blob, which won't trigger this kind of
        #   validation failure
        
        test_lines = list(lines)
        if line.startswith("directory-signature "):
          break
        
        # duplicates the line
        test_lines.insert(index, line)
        
        content = "\n".join(test_lines)
        self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
        NetworkStatusDocumentV3(content, False)  # constructs without validation
  
  def test_version(self):
    """
    Parses the network-status-version field, including trying to handle a
    different document version with the v3 parser.
    """
    
    document = get_network_status_document_v3({"network-status-version": "3"})
    self.assertEquals(3, document.version)
    self.assertEquals(None, document.version_flavor)
    self.assertEquals(False, document.is_microdescriptor)
    
    document = get_network_status_document_v3({"network-status-version": "3 microdesc"})
    self.assertEquals(3, document.version)
    self.assertEquals('microdesc', document.version_flavor)
    self.assertEquals(True, document.is_microdescriptor)
    
    content = get_network_status_document_v3({"network-status-version": "4"}, content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals(4, document.version)
    self.assertEquals(None, document.version_flavor)
    self.assertEquals(False, document.is_microdescriptor)
  
  def test_vote_status(self):
    """
    Parses the vote-status field.
    """
    
    document = get_network_status_document_v3({"vote-status": "vote"})
    self.assertEquals(False, document.is_consensus)
    self.assertEquals(True, document.is_vote)
    
    content = get_network_status_document_v3({"vote-status": "consensus"}, content = True)
    document = NetworkStatusDocumentV3(content)
    self.assertEquals(True, document.is_consensus)
    self.assertEquals(False, document.is_vote)
    
    test_values = (
      "",
      "   ",
      "votee",
    )
    
    for test_value in test_values:
      content = get_network_status_document_v3({"vote-status": test_value}, content = True)
      self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
      
      document = NetworkStatusDocumentV3(content, False)
      self.assertEquals(True, document.is_consensus)
      self.assertEquals(False, document.is_vote)
  
  def test_consensus_methods(self):
    """
    Parses the consensus-methods field.
    """
    
    document = get_network_status_document_v3({"vote-status": "vote", "consensus-methods": "12 3 1 780"})
    self.assertEquals([12, 3, 1, 780], document.consensus_methods)
    
    # check that we default to including consensus-method 1
    content = get_network_status_document_v3({"vote-status": "vote"}, ("consensus-methods",), content = True)
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals([1], document.consensus_methods)
    self.assertEquals(None, document.consensus_method)
    
    test_values = (
      ("", []),
      ("   ", []),
      ("1 2 3 a 5", [1, 2, 3, 5]),
      ("1 2 3 4.0 5", [1, 2, 3, 5]),
      ("2 3 4", [2, 3, 4]),  # spec says version one must be included
    )
    
    for test_value, expected_consensus_methods in test_values:
      content = get_network_status_document_v3({"vote-status": "vote", "consensus-methods": test_value}, content = True)
      self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
      
      document = NetworkStatusDocumentV3(content, False)
      self.assertEquals(expected_consensus_methods, document.consensus_methods)
  
  def test_consensus_method(self):
    """
    Parses the consensus-method field.
    """
    
    document = get_network_status_document_v3({"consensus-method": "12"})
    self.assertEquals(12, document.consensus_method)
    
    # check that we default to being consensus-method 1
    content = get_network_status_document_v3(exclude = ("consensus-method",), content = True)
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals(1, document.consensus_method)
    self.assertEquals([], document.consensus_methods)
    
    test_values = (
      "",
      "   ",
      "a",
      "1 2",
      "2.0",
    )
    
    for test_value in test_values:
      content = get_network_status_document_v3({"consensus-method": test_value}, content = True)
      self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
      
      document = NetworkStatusDocumentV3(content, False)
      self.assertEquals(1, document.consensus_method)
  
  def test_time_fields(self):
    """
    Parses invalid published, valid-after, fresh-until, and valid-until fields.
    All are simply datetime values.
    """
    
    expected = datetime.datetime(2012, 9, 2, 22, 0, 0)
    test_value = "2012-09-02 22:00:00"
    
    document = get_network_status_document_v3({
      "vote-status": "vote",
      "published": test_value,
      "valid-after": test_value,
      "fresh-until": test_value,
      "valid-until": test_value,
    })
    
    self.assertEquals(expected, document.published)
    self.assertEquals(expected, document.valid_after)
    self.assertEquals(expected, document.fresh_until)
    self.assertEquals(expected, document.valid_until)
    
    test_values = (
      "",
      "   ",
      "2012-12-12",
      "2012-12-12 01:01:",
      "2012-12-12 01:a1:01",
    )
    
    for field in ('published', 'valid-after', 'fresh-until', 'valid-until'):
      attr = field.replace('-', '_')
      
      for test_value in test_values:
        content = get_network_status_document_v3({"vote-status": "vote", field: test_value}, content = True)
        self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
        
        document = NetworkStatusDocumentV3(content, False)
        self.assertEquals(None, getattr(document, attr))
  
  def test_voting_delay(self):
    """
    Parses the voting-delay field.
    """
    
    document = get_network_status_document_v3({"voting-delay": "12 345"})
    self.assertEquals(12, document.vote_delay)
    self.assertEquals(345, document.dist_delay)
    
    test_values = (
      "",
      "   ",
      "1 a",
      "1\t2",
      "1 2.0",
    )
    
    for test_value in test_values:
      content = get_network_status_document_v3({"voting-delay": test_value}, content = True)
      self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
      
      document = NetworkStatusDocumentV3(content, False)
      self.assertEquals(None, document.vote_delay)
      self.assertEquals(None, document.dist_delay)
  
  def test_version_lists(self):
    """
    Parses client-versions and server-versions fields. Both are comma separated
    lists of tor versions.
    """
    
    expected = [stem.version.Version("1.2.3.4"), stem.version.Version("56.789.12.34-alpha")]
    test_value = "1.2.3.4,56.789.12.34-alpha"
    
    document = get_network_status_document_v3({"client-versions": test_value, "server-versions": test_value})
    self.assertEquals(expected, document.client_versions)
    self.assertEquals(expected, document.server_versions)
    
    test_values = (
      ("", []),
      ("   ", []),
      ("1.2.3.4,", [stem.version.Version("1.2.3.4")]),
      ("1.2.3.4,1.2.3.a", [stem.version.Version("1.2.3.4")]),
    )
    
    for field in ('client-versions', 'server-versions'):
      attr = field.replace('-', '_')
      
      for test_value, expected_value in test_values:
        content = get_network_status_document_v3({field: test_value}, content = True)
        self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
        
        document = NetworkStatusDocumentV3(content, False)
        self.assertEquals(expected_value, getattr(document, attr))
  
  def test_known_flags(self):
    """
    Parses some known-flag entries. Just exercising the field, there's not much
    to test here.
    """
    
    test_values = (
      ("", []),
      ("   ", []),
      ("BadExit", [Flag.BADEXIT]),
      ("BadExit ", [Flag.BADEXIT]),
      ("BadExit   ", [Flag.BADEXIT]),
      ("BadExit Fast", [Flag.BADEXIT, Flag.FAST]),
      ("BadExit Unrecognized Fast", [Flag.BADEXIT, "Unrecognized", Flag.FAST]),
    )
    
    for test_value, expected_value in test_values:
      document = get_network_status_document_v3({"known-flags": test_value})
      self.assertEquals(expected_value, document.known_flags)
  
  def test_params(self):
    """
    General testing for the 'params' line, exercising the happy cases.
    """
    
    document = get_network_status_document_v3({"params": "CircuitPriorityHalflifeMsec=30000 bwauthpid=1 unrecognized=-122"})
    self.assertEquals(30000, document.params["CircuitPriorityHalflifeMsec"])
    self.assertEquals(1, document.params["bwauthpid"])
    self.assertEquals(-122, document.params["unrecognized"])
    
    # empty params line
    content = get_network_status_document_v3({"params": ""}, content = True)
    document = NetworkStatusDocumentV3(content, default_params = True)
    self.assertEquals(DEFAULT_PARAMS, document.params)
    
    content = get_network_status_document_v3({"params": ""}, content = True)
    document = NetworkStatusDocumentV3(content, default_params = False)
    self.assertEquals({}, document.params)
  
  def test_params_malformed(self):
    """
    Parses a 'params' line with malformed content.
    """
    
    test_values = (
      "foo=",
      "foo=abc",
      "foo=+123",
      "foo=12\tbar=12",
    )
    
    for test_value in test_values:
      content = get_network_status_document_v3({"params": test_value}, content = True)
      self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
      
      document = NetworkStatusDocumentV3(content, False)
      self.assertEquals(DEFAULT_PARAMS, document.params)
  
  def test_params_range(self):
    """
    Check both the furthest valid 'params' values and values that are out of
    bounds.
    """
    
    test_values = (
      ("foo=2147483648", {"foo": 2147483648}, False),
      ("foo=-2147483649", {"foo": -2147483649}, False),
      ("foo=2147483647", {"foo": 2147483647}, True),
      ("foo=-2147483648", {"foo": -2147483648}, True),
      
      # param with special range constraints
      ("circwindow=99", {"circwindow": 99}, False),
      ("circwindow=1001", {"circwindow": 1001}, False),
      ("circwindow=500", {"circwindow": 500}, True),
      
      # param that relies on another param for its constraints
      ("cbtclosequantile=79 cbtquantile=80", {"cbtclosequantile": 79, "cbtquantile": 80}, False),
      ("cbtclosequantile=80 cbtquantile=80", {"cbtclosequantile": 80, "cbtquantile": 80}, True),
    )
    
    for test_value, expected_value, is_ok in test_values:
      content = get_network_status_document_v3({"params": test_value}, content = True)
      
      if is_ok:
        document = NetworkStatusDocumentV3(content, default_params = False)
      else:
        self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
        document = NetworkStatusDocumentV3(content, False, default_params = False)
      
      self.assertEquals(expected_value, document.params)
  
  def test_params_misordered(self):
    """
    Check that the 'params' line is rejected if out of order.
    """
    
    content = get_network_status_document_v3({"params": "unrecognized=-122 bwauthpid=1"}, content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, False, default_params = False)
    self.assertEquals({"unrecognized": -122, "bwauthpid": 1}, document.params)
  
  def test_footer_consensus_method_requirement(self):
    """
    Check that validation will notice if a footer appears before it was
    introduced.
    """
    
    content = get_network_status_document_v3({"consensus-method": "8"}, content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEqual([DOC_SIG], document.signatures)
    self.assertEqual([], document.get_unrecognized_lines())
    
    # excludes a footer from a version that shouldn't have it
    
    document = get_network_status_document_v3({"consensus-method": "8"}, ("directory-footer", "directory-signature"))
    self.assertEqual([], document.signatures)
    self.assertEqual([], document.get_unrecognized_lines())
  
  def test_footer_with_value(self):
    """
    Tries to parse a descriptor with content on the 'directory-footer' line.
    """
    
    content = get_network_status_document_v3({"directory-footer": "blarg"}, content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEqual([DOC_SIG], document.signatures)
    self.assertEqual([], document.get_unrecognized_lines())
  
  def test_bandwidth_wights_ok(self):
    """
    Parses a properly formed 'bandwidth-wights' line. Negative bandwidth
    weights might or might not be valid. The spec doesn't say, so making sure
    that we accept them.
    """
    
    weight_entries, expected = [], {}
    
    for index, key in enumerate(BANDWIDTH_WEIGHT_ENTRIES):
      weight_entries.append("%s=%i" % (key, index - 5))
      expected[key] = index - 5
    
    document = get_network_status_document_v3({"bandwidth-weights": " ".join(weight_entries)})
    self.assertEquals(expected, document.bandwidth_weights)
  
  def test_bandwidth_wights_malformed(self):
    """
    Provides malformed content in the 'bandwidth-wights' line.
    """
    
    test_values = (
      "Wbe",
      "Wbe=",
      "Wbe=a",
      "Wbe=+7",
    )
    
    base_weight_entry = " ".join(["%s=5" % e for e in BANDWIDTH_WEIGHT_ENTRIES])
    expected = dict([(e, 5) for e in BANDWIDTH_WEIGHT_ENTRIES if e != "Wbe"])
    
    for test_value in test_values:
      weight_entry = base_weight_entry.replace("Wbe=5", test_value)
      content = get_network_status_document_v3({"bandwidth-weights": weight_entry}, content = True)
      
      self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
      document = NetworkStatusDocumentV3(content, False)
      self.assertEquals(expected, document.bandwidth_weights)
  
  def test_bandwidth_wights_misordered(self):
    """
    Check that the 'bandwidth-wights' line is rejected if out of order.
    """
    
    weight_entry = " ".join(["%s=5" % e for e in reversed(BANDWIDTH_WEIGHT_ENTRIES)])
    expected = dict([(e, 5) for e in BANDWIDTH_WEIGHT_ENTRIES])
    
    content = get_network_status_document_v3({"bandwidth-weights": weight_entry}, content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals(expected, document.bandwidth_weights)
  
  def test_bandwidth_wights_in_vote(self):
    """
    Tries adding a 'bandwidth-wights' line to a vote.
    """
    
    weight_entry = " ".join(["%s=5" % e for e in BANDWIDTH_WEIGHT_ENTRIES])
    expected = dict([(e, 5) for e in BANDWIDTH_WEIGHT_ENTRIES])
    
    content = get_network_status_document_v3({"vote-status": "vote", "bandwidth-weights": weight_entry}, content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals(expected, document.bandwidth_weights)
  
  def test_bandwidth_wights_omissions(self):
    """
    Leaves entries out of the 'bandwidth-wights' line.
    """
    
    # try parsing an empty value
    
    content = get_network_status_document_v3({"bandwidth-weights": ""}, content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals({}, document.bandwidth_weights)
    
    # drop individual values
    
    for missing_entry in BANDWIDTH_WEIGHT_ENTRIES:
      weight_entries = ["%s=5" % e for e in BANDWIDTH_WEIGHT_ENTRIES if e != missing_entry]
      expected = dict([(e, 5) for e in BANDWIDTH_WEIGHT_ENTRIES if e != missing_entry])
      
      content = get_network_status_document_v3({"bandwidth-weights": " ".join(weight_entries)}, content = True)
      self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
      
      document = NetworkStatusDocumentV3(content, False)
      self.assertEquals(expected, document.bandwidth_weights)
  
  def test_microdescriptor_signature(self):
    """
    The 'directory-signature' lines both with and without a defined method for
    the signature format.
    """
    
    # including the signature method field should work
    
    document = get_network_status_document_v3({
      "network-status-version": "3 microdesc",
      "directory-signature": "sha256 " + NETWORK_STATUS_DOCUMENT_FOOTER[2][1],
    })
    
    self.assertEqual('sha256', document.signatures[0].method)
    
    # excluding the method should default to sha1
    
    document = get_network_status_document_v3({
      "network-status-version": "3 microdesc",
    })
    
    self.assertEqual('sha1', document.signatures[0].method)
  
  def test_malformed_signature(self):
    """
    Provides malformed or missing content in the 'directory-signature' line.
    """
    
    test_values = (
      "",
      "\n",
      "blarg",
    )
    
    for test_value in test_values:
      for test_attr in xrange(3):
        attrs = [DOC_SIG.identity, DOC_SIG.key_digest, DOC_SIG.signature]
        attrs[test_attr] = test_value
        
        content = get_network_status_document_v3({"directory-signature": "%s %s\n%s" % tuple(attrs)}, content = True)
        self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
        NetworkStatusDocumentV3(content, False)  # checks that it's still parsable without validation
  
  def test_with_router_status_entries(self):
    """
    Includes router status entries within the document. This isn't to test the
    RouterStatusEntry parsing but rather the inclusion of it within the
    document.
    """
    
    entry1 = get_router_status_entry_v3({'s': "Fast"})
    entry2 = get_router_status_entry_v3({'s': "Valid"})
    document = get_network_status_document_v3(routers = (entry1, entry2))
    
    self.assertEquals((entry1, entry2), document.routers)
    
    # try with an invalid RouterStatusEntry
    
    entry3 = RouterStatusEntryV3(get_router_status_entry_v3({'r': "ugabuga"}, content = True), False)
    content = get_network_status_document_v3(routers = (entry3,), content = True)
    
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals((entry3,), document.routers)
    
    # try including with a microdescriptor consensus
    
    content = get_network_status_document_v3({"network-status-version": "3 microdesc"}, routers = (entry1, entry2), content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    expected_routers = (
      RouterStatusEntryMicroV3(str(entry1), False),
      RouterStatusEntryMicroV3(str(entry2), False),
    )
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals(expected_routers, document.routers)
  
  def test_with_microdescriptor_router_status_entries(self):
    """
    Includes microdescriptor flavored router status entries within the
    document.
    """
    
    entry1 = get_router_status_entry_micro_v3({'s': "Fast"})
    entry2 = get_router_status_entry_micro_v3({'s': "Valid"})
    document = get_network_status_document_v3({"network-status-version": "3 microdesc"}, routers = (entry1, entry2))
    
    self.assertEquals((entry1, entry2), document.routers)
    
    # try with an invalid RouterStatusEntry
    
    entry3 = RouterStatusEntryMicroV3(get_router_status_entry_micro_v3({'r': "ugabuga"}, content = True), False)
    content = get_network_status_document_v3({"network-status-version": "3 microdesc"}, routers = (entry3,), content = True)
    
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals((entry3,), document.routers)
    
    # try including microdescriptor entries in a normal consensus
    
    content = get_network_status_document_v3(routers = (entry1, entry2), content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    expected_routers = (
      RouterStatusEntryV3(str(entry1), False),
      RouterStatusEntryV3(str(entry2), False),
    )
    
    document = NetworkStatusDocumentV3(content, False)
    self.assertEquals(expected_routers, document.routers)
  
  def test_with_directory_authorities(self):
    """
    Includes a couple directory authorities in the document.
    """
    
    for is_document_vote in (False, True):
      for is_authorities_vote in (False, True):
        authority1 = get_directory_authority({'contact': 'doctor jekyll'}, is_vote = is_authorities_vote)
        authority2 = get_directory_authority({'contact': 'mister hyde'}, is_vote = is_authorities_vote)
        
        vote_status = "vote" if is_document_vote else "consensus"
        content = get_network_status_document_v3({"vote-status": vote_status}, authorities = (authority1, authority2), content = True)
        
        if is_document_vote == is_authorities_vote:
          document = NetworkStatusDocumentV3(content)
          self.assertEquals((authority1, authority2), document.directory_authorities)
        else:
          # authority votes in a consensus or consensus authorities in a vote
          self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
          document = NetworkStatusDocumentV3(content, validate = False)
          self.assertEquals((authority1, authority2), document.directory_authorities)
  
  def test_authority_validation_flag_propagation(self):
    """
    Includes invalid certificate content in an authority entry. This is testing
    that the 'validate' flag propagages from the document to authority, and
    authority to certificate classes.
    """
    
    # make the dir-key-published field of the certiciate be malformed
    authority_content = get_directory_authority(is_vote = True, content = True)
    authority_content = authority_content.replace("dir-key-published 2011", "dir-key-published 2011a")
    
    content = get_network_status_document_v3({"vote-status": "vote"}, authorities = (authority_content,), content = True)
    self.assertRaises(ValueError, NetworkStatusDocumentV3, content)
    
    document = NetworkStatusDocumentV3(content, validate = False)
    self.assertEquals((DirectoryAuthority(authority_content, False, True),), document.directory_authorities)
