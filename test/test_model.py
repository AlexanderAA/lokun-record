#! /usr/bin/python2
# coding: utf8
import sys
sys.path.append("..")
import unittest
import os

from record import model
from record import config
from record import hashing


DB_NAME = '/tmp/testing.db'


def mock_noop(*args, **kwargs):
    pass

def mock_false(*args, **kwargs):
    return False

class TestNode(unittest.TestCase):
    def verify(self, testnode, name, ip, heartbeat=0, selfcheck=False, uptime='0d 0h', usercount=0, cpu=0.0, enabled=False, is_exit=False):
            self.assertEquals(testnode.name, name)
            self.assertEquals(testnode.ip, ip)
            self.assertEquals(testnode.heartbeat, heartbeat)
            self.assertEquals(testnode.selfcheck, selfcheck)
            self.assertEquals(testnode.uptime, uptime)
            self.assertEquals(testnode.usercount, usercount)
            self.assertEquals(testnode.cpu, cpu)
            self.assertEquals(testnode.enabled, enabled)
            self.assertEquals(testnode.is_exit, is_exit)
            self.assertTrue(type(testnode.name) in [str, unicode])
            self.assertTrue(type(testnode.ip) in [str, unicode])
            self.assertIs(type(testnode.heartbeat), int)
            self.assertIs(type(testnode.selfcheck), bool)
            self.assertTrue(type(testnode.uptime) in [unicode, str])
            self.assertIs(type(testnode.usercount), int)
            self.assertIs(type(testnode.cpu), float)
            self.assertIs(type(testnode.enabled), bool)
            self.assertIs(type(testnode.is_exit), bool)
            self.assertTrue(testnode.score >= 0)

    def compare(self, node1, node2):
        self.verify(node1, node2.name, node2.ip, heartbeat=node2.heartbeat, selfcheck=node2.selfcheck, uptime=node2.uptime, usercount=node2.usercount, cpu=node2.cpu, enabled=node2.enabled, is_exit=node2.is_exit)

    def setUp(self):
        model.new_db(DB_NAME)
        config.db = DB_NAME

    def tearDown(self):
        os.remove(DB_NAME)
        
    def test_bad_new_node(self):
        model.Node.new("samenode", "1.1.1.1")
        self.assertRaises(ValueError, model.Node.new, "samenode", "1.1.1.2")
        self.assertRaises(ValueError, model.Node.new, "err", "err")

    def test_node_no_save(self):
        testnode = model.Node.new('nosave', "1.1.1.1")
        self.verify(testnode, "nosave", "1.1.1.1")

    def test_node_save(self):
        testnode = model.Node.new('save', "1.1.1.1")
        testnode.save()
        getnode = model.Node.get("save")
        self.compare(testnode, getnode)

    def test_node_and_key(self):
        testnode = model.Node.new('keynode', "1.1.1.1")
        testkey = model.APIKey.new("keynode", status="new")
        self.assertRaises(ValueError, model.Node.auth, "keynode", testkey.key)
        testkey.status = "good"
        testkey.save()
        model.Node.auth("keynode", testkey.key)

    def test_node_enabled(self):
        enablednode = model.Node.new('enabled', '1.1.1.1')
        enablednode.update(selfcheck=True)
        enablednode.enabled = True
        enablednode.save()
        # When a node is enabled it is either alive
        self.assertTrue(enablednode.alive and not enablednode.down)
        # or down
        enablednode.update(selfcheck=False)
        self.assertTrue(enablednode.down and not enablednode.alive)
        # When a node is disabled, it's never 'down' (because status should report
        # on a disabled node. 
        disablednode = model.Node.new('disabled', '2.2.2.2')
        disablednode.update(selfcheck=False)
        disablednode.save()
        self.assertTrue(not disablednode.down)
        disablednode.update(selfcheck=True)
        disablednode.save()
        # Should still be alive even though it is disabled
        self.assertTrue(disablednode.alive)
        

    def test_is_exit(self):
        exit1 = model.Node.new('exit', '1.1.1.1', is_exit=True)
        exit2 = model.Node.get('exit')
        self.compare(exit1, exit2)

    def test_nodelist(self):
        downnode = model.Node.new('down', '1.1.1.1')
        downnode.enabled = True
        downnode.save()
        
        nodenames = lambda f: [a.name for a in f()]
        self.compare(model.NodeList.down()[0], downnode)

        self.assertTrue("down" in nodenames(model.NodeList.down))
        self.assertTrue("down" in nodenames(model.NodeList.get))
        self.assertTrue("down" not in nodenames(model.NodeList.best))
        self.assertTrue("down" not in nodenames(model.NodeList.alive))

        disablednode = model.Node.new('disabled', '1.1.1.1')
        disablednode.enabled = False
        disablednode.update(selfcheck=True)
        disablednode.save()
        self.assertTrue("disabled" not in nodenames(model.NodeList.down))
        self.assertTrue("disabled" in nodenames(model.NodeList.get))
        self.assertTrue("disabled" not in nodenames(model.NodeList.best))
        self.assertTrue("disabled" in nodenames(model.NodeList.alive))
        # and if we enabled it :)
        disablednode.enabled = True
        disablednode.save()
        self.assertTrue("disabled" in nodenames(model.NodeList.best))

    def test_node_update_save(self):
        newnode = model.Node.new('node', "1.1.1.1")
        # Doing it in the same manner as restapi.py does it
        getnode = model.Node.get("node")


        usercount = int("2")
        throughput = int("123")
        total_throughput = int("1234")
        uptime = "1d 0h"
        cpu = float("80.73")
        selfcheck = True

        getnode.update(usercount=usercount, throughput=throughput, total_throughput=total_throughput, uptime=uptime, cpu=cpu, selfcheck=selfcheck)
        heartbeat = getnode.heartbeat
        getnode.enabled = True
        getnode.save()
        
        self.assertTrue(getnode.score >= 100)

        self.verify(getnode, "node", "1.1.1.1", usercount=2, heartbeat=heartbeat, uptime="1d 0h", cpu=80.73, selfcheck=True, enabled=True)
        
        getnode.save()
        updatednode = model.Node.get("node")

        self.assertTrue(updatednode.score >= 100)
        self.compare(updatednode, getnode)
            

class TestUser(unittest.TestCase):
    def verify(self, testuser, username, passwd, email='', dl_left=0, credit_isk=0):
        self.assertEquals(testuser.username, username)
        self.assertTrue(model.compare_passwd(passwd, testuser.hashed_passwd))
        self.assertEquals(testuser.email, email)
        self.assertEquals(testuser.dl_left, dl_left)
        self.assertEquals(testuser.credit_isk, credit_isk)

    def setUp(self):
        model.new_db(DB_NAME)
        config.db = DB_NAME

        # Those are not under test. Hurray for monkeypatched dependency injection!
        self.real_mkkeys = model.User.mkkeys
        model.User.mkkeys = mock_noop
        self.real_mkinstaller = model.User.mkinstaller
        model.User.mkinstaller = mock_noop

        self.invkeys = [model.InviteKey.new().key for _ in xrange(10)]

    def tearDown(self):
        os.remove(DB_NAME)
        model.User.mkkeys = self.real_mkkeys
        model.User.mkinstaller = self.real_mkinstaller

    def test_bad_user(self):
        self.assertRaises(ValueError, model.User.new, 'baduser1', 'validpassword', 'invalidinvkey')
        self.assertRaises(ValueError, model.User.new, 'baduser1', 'badpass')
        self.assertRaises(ValueError, model.User.new, 'baduser1', range(10)+['bad type'], self.invkeys.pop())
        model.User.new('samename', 'validpassword')
        self.assertRaises(ValueError, model.User.new, 'samename', 'validpassword')

    
    def test_user_no_save(self):
        testuser = model.User.new('testusernosave', '_hunter2', self.invkeys.pop())
        self.verify(testuser, 'testusernosave', '_hunter2')

    def test_user_no_email(self):
        testuser = model.User.new('testusernoemail', '_hunter3', self.invkeys.pop())
        self.verify(testuser, 'testusernoemail', '_hunter3')
        testuser.save()
        returneduser = model.User.get('testusernoemail')
        self.verify(returneduser, 'testusernoemail', '_hunter3')

    def test_user_with_more_stuff(self):
        testuser = model.User.new('testuserwithstuff', '_hunter2', self.invkeys.pop(), 'rawr@example.com')
        testuser.dl_left = 822
        testuser.credit_isk = 2000
        self.verify(testuser, 'testuserwithstuff', '_hunter2', 'rawr@example.com', 822, 2000)
        testuser.save()
        returneduser = model.User.get('testuserwithstuff')
        self.verify(returneduser, 'testuserwithstuff', '_hunter2', 'rawr@example.com', 822, 2000)

    def test_user_buy_sub(self):
        pooruser = model.User.new("pooruser", "_hunter2", None, None)
        pooruser.credit_isk = 1000
        # monkey patching :) (otherwise an exception about btcprices table being empty
        # is raised. 
        self.real_buy_sub_btc = model.User.buy_sub_btc
        model.User.buy_sub_btc = mock_false
        self.assertRaises(model.NotEnoughFundsError, pooruser.buy_sub)
        self.assertEquals(pooruser.sub_active, False)
        payinguser = model.User.new("payinguser", "_hunter2", None, None)
        payinguser.credit_isk = 2000
        payinguser.buy_sub()
        self.assertEquals(payinguser.sub_active, True)

class TestInviteKey(unittest.TestCase):
    def setUp(self):
        model.new_db(DB_NAME)
        config.db = DB_NAME

    def tearDown(self):
        os.remove(DB_NAME)
    
    def test_new_key(self):
        k = model.InviteKey.new()
        self.assertTrue(len(k.key) > 0)
        self.assertIsInstance(k.key, str)

    def test_invalid(self):
        k = model.InviteKey('notarealkey')
        self.assertFalse(k.valid)
        self.assertRaises(ValueError, k.use)
        k = model.InviteKey('')
        self.assertFalse(k.valid)
        self.assertRaises(ValueError, k.use)

    def test_using(self):
        k = model.InviteKey.new()
        val = k.key
        del k
        k = model.InviteKey(val)
        self.assertTrue(k.valid)
        k.use()
        self.assertFalse(k.valid)
        self.assertRaises(ValueError, k.use)
        del k
        k = model.InviteKey(val)
        self.assertFalse(k.valid)
        self.assertRaises(ValueError, k.use)


class TestAPIKey(unittest.TestCase):
    def verify(self, testkey, key, name, status):
            self.assertEquals(testkey.key, key)
            self.assertEquals(testkey.name, name)
            self.assertEquals(testkey.status, status)
            self.assertIs(type(testkey.key), str)
            self.assertIs(type(testkey.name), str)
            self.assertIs(type(testkey.status), str)

    def compare(self, key1, key2):
        self.verify(key1, key2.key, key2.name, key2.status)

    def setUp(self):
        model.new_db(DB_NAME)
        config.db = DB_NAME
        self.alwaysvalid = model.APIKey.new("validkey")
        model.APIKey.new("revokedkey", status="revoked")

    def tearDown(self):
        os.remove(DB_NAME)

    def test_alwaysvalid(self):
        authed = model.APIKey.auth(self.alwaysvalid.key)
        # also test with name
        model.APIKey.auth(self.alwaysvalid.key, "validkey")
        self.verify(self.alwaysvalid, authed.key, authed.name, authed.status)

    def test_bad_key(self):
        for _ in xrange(20):
            rndkey = hashing.gen_randhex_sha256()
            self.assertRaises(ValueError, model.APIKey.auth, rndkey)

    def test_new_good_key(self):
        testkey = model.APIKey.new("goodtestkey", status="good")
        authed = model.APIKey.auth(testkey.key)
        self.verify(testkey, authed.key, authed.name, authed.status)

    def test_new_revoked_key(self):
        testkey = model.APIKey.new("revokedtestkey", status="revoked")
        self.assertRaises(ValueError, model.APIKey.auth, testkey.key)

    def test_revoking_new_key(self):
        testkey = model.APIKey.new("revokeme", status="good")
        authed = model.APIKey.auth(testkey.key)
        # also test with name
        model.APIKey.auth(testkey.key, "revokeme")
        self.verify(testkey, authed.key, authed.name, authed.status)
        testkey.status = "revoked"
        testkey.save()
        self.assertRaises(ValueError, model.APIKey.auth, testkey.key)

    def test_get_by_name(self):
        newkey = model.APIKey.new("newkey1")
        get_newkey_list = model.APIKey.get_by_name("newkey1")
        self.assertIs(type(get_newkey_list), list)
        get_newkey = get_newkey_list[0]
        self.assertIs(type(get_newkey), model.APIKey)
        self.compare(newkey, get_newkey)
        
        

if __name__ == '__main__':
    unittest.main()
