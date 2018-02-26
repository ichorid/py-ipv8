from base64 import b64encode
import random
import unittest

from ipv8.keyvault.crypto import ECCrypto
from ipv8.peer import Peer
from ipv8.peerdiscovery.network import Network


def _generate_peer():
    key = ECCrypto().generate_key(u'very-low')
    address = (".".join([str(random.randint(0, 255)) for _ in range(4)]), random.randint(0, 65535))
    return Peer(key, address)


class TestNetwork(unittest.TestCase):

    peers = [_generate_peer() for _ in range(4)]

    def setUp(self):
        self.network = Network()

    def test_discover_address(self):
        """
        Check registration of introducer and introduced when a new address is discovered.

        The introducer should be verified and not walkable.
        The introduced should not be verified and walkable.
        """
        self.network.discover_address(self.peers[0], self.peers[1].address)

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[1].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)
        self.assertNotIn(self.peers[1], self.network.verified_peers)
        self.assertIn(self.peers[1].address, self.network.get_introductions_from(self.peers[0]))
        self.assertTrue(self.network.graph.has_edge(b64encode(self.peers[0].mid), self.peers[1].address))

    def test_discover_address_duplicate(self):
        """
        Check registration of introducer and introduced when the same address is discovered twice.
        """
        self.network.discover_address(self.peers[0], self.peers[1].address)
        self.network.discover_address(self.peers[0], self.peers[1].address)

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[1].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)
        self.assertNotIn(self.peers[1], self.network.verified_peers)
        self.assertIn(self.peers[1].address, self.network.get_introductions_from(self.peers[0]))
        self.assertTrue(self.network.graph.has_edge(b64encode(self.peers[0].mid), self.peers[1].address))

    def test_discover_address_known(self):
        """
        Check if an address is already known, the network isn't updated.
        """
        self.network.discover_address(self.peers[0], self.peers[1].address)
        self.network.discover_address(self.peers[2], self.peers[1].address)

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[1].address, self.network.get_walkable_addresses())
        self.assertNotIn(self.peers[2].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)
        self.assertNotIn(self.peers[1], self.network.verified_peers)
        self.assertIn(self.peers[2], self.network.verified_peers)
        self.assertIn(self.peers[1].address, self.network.get_introductions_from(self.peers[0]))
        self.assertTrue(self.network.graph.has_edge(b64encode(self.peers[0].mid), self.peers[1].address))

    def test_discover_address_known_parent_deceased(self):
        """
        Check if an address is already known, the new introducer adopts the introduced.
        """
        self.network.discover_address(self.peers[0], self.peers[1].address)
        self.network.remove_peer(self.peers[0])
        self.network.discover_address(self.peers[2], self.peers[1].address)

        self.assertIn(self.peers[1].address, self.network.get_walkable_addresses())
        self.assertNotIn(self.peers[2].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[2], self.network.verified_peers)
        self.assertNotIn(self.peers[1], self.network.verified_peers)
        self.assertIn(self.peers[1].address, self.network.get_introductions_from(self.peers[2]))
        self.assertTrue(self.network.graph.has_edge(b64encode(self.peers[2].mid), self.peers[1].address))

    def test_discover_address_blacklist(self):
        """
        Check if an address is in the blacklist, the network isn't updated.
        """
        self.network.blacklist.append(self.peers[2].address)
        self.network.discover_address(self.peers[0], self.peers[1].address)
        self.network.discover_address(self.peers[0], self.peers[2].address)

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[1].address, self.network.get_walkable_addresses())
        self.assertNotIn(self.peers[2].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)
        self.assertNotIn(self.peers[1], self.network.verified_peers)
        self.assertNotIn(self.peers[2], self.network.verified_peers)
        self.assertIn(self.peers[1].address, self.network.get_introductions_from(self.peers[0]))
        self.assertTrue(self.network.graph.has_edge(b64encode(self.peers[0].mid), self.peers[1].address))

    def test_discover_address_multiple(self):
        """
        Check if a single peer can perform multiple introductions.
        """
        self.network.discover_address(self.peers[0], self.peers[1].address)
        self.network.discover_address(self.peers[0], self.peers[2].address)

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)

        for other in [1, 2]:
            self.assertIn(self.peers[other].address, self.network.get_walkable_addresses())
            self.assertNotIn(self.peers[other], self.network.verified_peers)
            self.assertIn(self.peers[other].address, self.network.get_introductions_from(self.peers[0]))
            self.assertTrue(self.network.graph.has_edge(b64encode(self.peers[0].mid), self.peers[other].address))

    def test_discover_services(self):
        """
        Check if services are properly registered for a peer.
        """
        service = "".join([chr(i) for i in range(20)])
        self.network.discover_services(self.peers[0], [service])
        self.network.add_verified_peer(self.peers[0])

        self.assertIn(service, self.network.get_services_for_peer(self.peers[0]))
        self.assertIn(self.peers[0], self.network.get_peers_for_service(service))

    def test_discover_services_unverified(self):
        """
        Check if services are properly registered for an unverified peer.

        You can query the services of an unverified peer, but it won't show up as a reachable peer for a service.
        """
        service = "".join([chr(i) for i in range(20)])
        self.network.discover_services(self.peers[0], [service])

        self.assertIn(service, self.network.get_services_for_peer(self.peers[0]))
        self.assertNotIn(self.peers[0], self.network.get_peers_for_service(service))

    def test_discover_services_update(self):
        """
        Check if services are properly combined for a peer.
        """
        service1 = "".join([chr(i) for i in range(20)])
        service2 = "".join([chr(i) for i in range(20, 40)])
        self.network.discover_services(self.peers[0], [service1])
        self.network.discover_services(self.peers[0], [service2])
        self.network.add_verified_peer(self.peers[0])

        self.assertIn(service1, self.network.get_services_for_peer(self.peers[0]))
        self.assertIn(service2, self.network.get_services_for_peer(self.peers[0]))
        self.assertIn(self.peers[0], self.network.get_peers_for_service(service1))
        self.assertIn(self.peers[0], self.network.get_peers_for_service(service2))

    def test_discover_services_update_overlap(self):
        """
        Check if services are properly combined when discovered services overlap.
        """
        service1 = "".join([chr(i) for i in range(20)])
        service2 = "".join([chr(i) for i in range(20, 40)])
        self.network.discover_services(self.peers[0], [service1])
        self.network.discover_services(self.peers[0], [service1, service2])
        self.network.add_verified_peer(self.peers[0])

        self.assertIn(service1, self.network.get_services_for_peer(self.peers[0]))
        self.assertIn(service2, self.network.get_services_for_peer(self.peers[0]))
        self.assertIn(self.peers[0], self.network.get_peers_for_service(service1))
        self.assertIn(self.peers[0], self.network.get_peers_for_service(service2))

    def test_add_verified_peer_new(self):
        """
        Check if a new verified peer can be added to the network.
        """
        self.network.add_verified_peer(self.peers[0])

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)
        self.assertListEqual([], self.network.get_introductions_from(self.peers[0]))
        self.assertTrue(self.network.graph.has_node(b64encode(self.peers[0].mid)))

    def test_add_verified_peer_blacklist(self):
        """
        Check if a new verified peer can be added to the network.
        """
        self.network.blacklist.append(self.peers[0].address)
        self.network.add_verified_peer(self.peers[0])

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertNotIn(self.peers[0], self.network.verified_peers)
        self.assertFalse(self.network.graph.has_node(b64encode(self.peers[0].mid)))

    def test_add_verified_peer_duplicate(self):
        """
        Check if an already verified (by slightly changed) peer doesn't cause duplicates in the network.
        """
        self.network.add_verified_peer(self.peers[0])
        self.peers[0].update_clock(1)
        self.network.add_verified_peer(self.peers[0])

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)
        self.assertListEqual([], self.network.get_introductions_from(self.peers[0]))
        self.assertTrue(self.network.graph.has_node(b64encode(self.peers[0].mid)))

    def test_add_verified_peer_promote(self):
        """
        Check if a peer can be promoted from an address to a verified peer.
        """
        self.network.discover_address(self.peers[1], self.peers[0].address)
        self.network.add_verified_peer(self.peers[0])

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertIn(self.peers[0], self.network.verified_peers)
        self.assertListEqual([], self.network.get_introductions_from(self.peers[0]))
        self.assertTrue(self.network.graph.has_node(b64encode(self.peers[0].mid)))
        self.assertFalse(self.network.graph.has_node(self.peers[0].address))

    def test_get_verified_by_address(self):
        """
        Check if we can find a peer in our network by its address.
        """
        self.network.add_verified_peer(self.peers[0])

        self.assertEqual(self.peers[0], self.network.get_verified_by_address(self.peers[0].address))

    def test_get_verified_by_public_key(self):
        """
        Check if we can find a peer in our network by its public key.
        """
        self.network.add_verified_peer(self.peers[0])

        self.assertEqual(self.peers[0],
                         self.network.get_verified_by_public_key_bin(self.peers[0].public_key.key_to_bin()))

    def test_remove_by_address(self):
        """
        Check if we can remove a peer from our network by its address.
        """
        self.network.add_verified_peer(self.peers[0])
        self.network.discover_services(self.peers[0], ["0"*20])
        self.network.remove_by_address(self.peers[0].address)

        self.assertNotIn(self.peers[0], self.network.verified_peers)
        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertEqual(set(), self.network.get_services_for_peer(self.peers[0]))
        self.assertFalse(self.network.graph.has_node(b64encode(self.peers[0].mid)))

    def test_remove_by_address_unverified(self):
        """
        Check if we can remove an unverified peer from our network by its address.
        """
        self.network.discover_address(self.peers[0], self.peers[1].address)
        self.network.remove_by_address(self.peers[1].address)

        self.assertNotIn(self.peers[1].address, self.network.get_walkable_addresses())
        self.assertFalse(self.network.graph.has_node(self.peers[1].address))

    def test_remove_by_address_unknown(self):
        """
        Removing unknown peers should not affect other peers.
        """
        self.network.add_verified_peer(self.peers[0])

        previous_walkable = self.network.get_walkable_addresses()
        previous_verified = self.network.verified_peers

        self.network.remove_by_address(self.peers[1].address)

        self.assertEqual(previous_walkable, self.network.get_walkable_addresses())
        self.assertEqual(previous_verified, self.network.verified_peers)

    def test_remove_by_address_no_services(self):
        """
        Check if we can remove a peer from our network if it doesn't have services by address.
        """
        self.network.add_verified_peer(self.peers[0])
        self.network.remove_by_address(self.peers[0].address)

        self.assertNotIn(self.peers[0], self.network.verified_peers)
        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertFalse(self.network.graph.has_node(b64encode(self.peers[0].mid)))

    def test_remove_peer(self):
        """
        Check if we can remove a peer from our network.
        """
        self.network.add_verified_peer(self.peers[0])
        self.network.discover_services(self.peers[0], ["0" * 20])
        self.network.remove_peer(self.peers[0])

        self.assertNotIn(self.peers[0], self.network.verified_peers)
        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertEqual(set(), self.network.get_services_for_peer(self.peers[0]))
        self.assertFalse(self.network.graph.has_node(b64encode(self.peers[0].mid)))

    def test_remove_peer_external(self):
        """
        Check if we can remove an externally created peer from our network.
        """
        self.network.discover_address(self.peers[1], self.peers[0].address)
        self.network.remove_peer(self.peers[0])

        self.assertNotIn(self.peers[0].address, self.network.get_walkable_addresses())
        self.assertFalse(self.network.graph.has_node(b64encode(self.peers[0].mid)))
        self.assertFalse(self.network.graph.has_node(self.peers[0].address))

    def test_remove_peer_unknown(self):
        """
        Removing unknown peers should not affect other peers.
        """
        self.network.add_verified_peer(self.peers[0])

        previous_walkable = self.network.get_walkable_addresses()
        previous_verified = self.network.verified_peers

        self.network.remove_peer(self.peers[1])

        self.assertEqual(previous_walkable, self.network.get_walkable_addresses())
        self.assertEqual(previous_verified, self.network.verified_peers)

    def test_get_walkable_by_service(self):
        """
        Check if we can retrieve walkable addresses by parent service id.
        """
        service = "".join([chr(i) for i in range(20)])
        self.network.discover_address(self.peers[2], self.peers[3].address)
        self.network.discover_address(self.peers[0], self.peers[1].address)
        self.network.discover_services(self.peers[0], [service])

        self.assertEqual([self.peers[1].address], self.network.get_walkable_addresses(service))
