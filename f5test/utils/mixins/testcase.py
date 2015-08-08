# Add your TestCase mixins here...
import sys
import logging
import f5test.commands.rest as RCMD
from f5test.interfaces.rest.emapi.objects.asm import CmAsmAllAsmDevicesGroup
from f5test.utils.wait import wait, wait_args

LOG = logging.getLogger(__name__)

# for big-ip
URL_TM_DEVICE_INFO = "/mgmt/shared/identified-devices/config/device-info"

class AsmTestCase(object):

    def device_rediscovery(self, device, biq_rstifc):
        # Remove the BIG-IP
        # Proceed when RMA fails in case device not DMA properly from previous test
        try:
            RCMD.device.delete_asm([device])
        except:
            LOG.debug("Unexpected RMA error: %s" % sys.exc_info()[0])

        # Ensure device is deleted from cm-asm-allAsmDevices group
        bip_rstifc = self.get_icontrol_rest(device=device).api
        resp = bip_rstifc.get(URL_TM_DEVICE_INFO)
        machineId = resp["machineId"]
        hostname = resp["hostname"]
        def query():
            resp = biq_rstifc.get(CmAsmAllAsmDevicesGroup.URI)
            return machineId not in [item.machineId for item in resp["items"]]
        wait(query, interval=1, timeout=180,
             timeout_message="BIGIP %s didn't get removed from asm device group 180s after RMA." % hostname)

        # Discover the BIG-IP.
        ret = RCMD.device.discover_asm([device], timeout=540)
        return ret

    def remove_keys(self, dictionary, keys_to_remove):
        """Return a copy of dictionary with specified keys removed."""
        if not keys_to_remove:
            return dictionary

        d = dict(dictionary)
        for key in keys_to_remove:
            if key in d:
                del d[key]
        return d

    def assert_hash_equal(self, hash1, hash2, keys_to_remove=None, msg=None):
        # Remove the keys that is independant on hash1 and hash2
        hash1_truncated = self.remove_keys(hash1, keys_to_remove)
        hash2_truncated = self.remove_keys(hash2, keys_to_remove)

        # Assert parameters in hash1 and hash2 are the same
        self.maxDiff = None
        LOG.debug("==>expected:" + str(hash1_truncated))
        LOG.debug("==>actual:" + str(hash2_truncated))
        self.assertDictEqual(hash1_truncated, hash2_truncated, msg=msg)

    def assert_array_of_hashes_equal(self, expected, actual, primary_key, keys_to_remove=None, msg=None):
        """This asserts that two array of hashes match each other.
        ex: both array has a hash that has the same description, "Illegal...",
        the following error msg means that, with the hash that has the same primary_key:
        1) hash of actual array doesn't have the missing key key1 which hash of expected array has.
        2) hash of actual array has addtional key key2 than hash of expected array.
        3) hash of actual array and hash of expected array have same key but diff values.

        [Hash with "description":"Illegal attachment in SOAP message"]
        [missing keys] "name":"key1"
        [additional keys] "name":"key2"
        [diff values] <key> violationReference
        [           ] <len diff> len_expected vs len_actual
        [           ] <expected val> {'link': 'https://localhost/mgmt/tm/asm/violations/tkmi0bSUBGtyF2frCc7ByA'}
        [           ] <actual val>   {'kind': 'cm:asm:working-config:violations:violationstate'...}
        """
        LOG.debug("==>expected:" + str(expected))
        LOG.debug("==>actual:" + str(actual))
        LOG.debug("primary_key's type:" + str(type(primary_key)) + "should eq <str>")
        LOG.debug("expected's type:" + str(type(expected)) + "should eq <list>")
        val_of_primary_key_list_expected = sorted([ hash[primary_key] for hash in expected ])
        val_of_primary_key_list_actual   = sorted([ hash[primary_key] for hash in actual ])
        # Assert both array has the same number of hash and same primary key values
        self.assertEqual(val_of_primary_key_list_expected, val_of_primary_key_list_actual)

        OK = 1
        msg = "\n"
        for hash_e in expected:
            for hash_a in actual:
                if hash_e[primary_key] == hash_a[primary_key]:
                    fail_msg = '[Hash with "%s":"%s"]'\
                                 %(primary_key, hash_e[primary_key]) + "\n"
                    # Remove the keys that is independant on bigip and bigiq
                    hash_e = self.remove_keys(hash_e, keys_to_remove)
                    hash_a = self.remove_keys(hash_a, keys_to_remove)

                    # Compare if the hash with same pk value has same keys
                    # As hash keys compared here isn't huge, iterates through multiple times
                    same_keys       = [key for key in hash_a.keys() if key in hash_e.keys()]
                    missing_keys    = [key for key in hash_e.keys() if key not in hash_a.keys()]
                    additional_keys = [key for key in hash_a.keys() if key not in hash_e.keys()]
                    if missing_keys:
                        OK = 0
                        missing_key_value_pair = [(key, hash_e[key]) for key in missing_keys]
                        for missing_key in missing_key_value_pair:
                            fail_msg += "[missing keys] " + \
                                        '"%s":"%s"'%(missing_key[0], missing_key[1]) + "\n"
                    if additional_keys:
                        OK = 0
                        additional_key_value_pair = [(key, hash_a[key]) for key in additional_keys]
                        for additional_key in additional_key_value_pair:
                            fail_msg += "[additional keys] " + \
                                        '"%s":"%s"'%(additional_key[0], additional_key[1]) + "\n"

                    wrong_value_for_same_key = {}
                    for key in same_keys:
                        if hash_a[key] != hash_e[key]:
                            OK = 0
                            fail_msg +=("[diff values] (key) %s\n" % key
                                       +"              (len diff) expected %s vs actual %s\n" % (len(hash_e[key]), len(hash_a[key]))
                                       +"              (expected val) %s\n" % repr(hash_e[key])
                                       +"              (actual   val) %s\n" % repr(hash_a[key]))

                    # If this comparison fails, add fail msg to the msg stack
                    if OK == 0:
                        msg += fail_msg
        if OK == 0:
            self.fail(msg)

    def assert_two_elements_equal(self, element1, element2,
                            keys_to_remove=None, primary_key=None, msg=None):
        """Element could be either a hash or an array of hashes."""
        LOG.debug("==>keys_to_remove:" + str(keys_to_remove))
        LOG.debug("==>msg:" + str(msg))
        if len(element1) == 0 and len(element2) == 0:
            self.fail("Items are empty!")
        elif len(element1) == 1 and len(element2) == 1:
            LOG.info("calling assert_hash_equal()")
            self.assert_hash_equal(element1[0], element2[0],
                                   keys_to_remove=keys_to_remove,
                                   msg=msg)
        elif len(element1) >= 1 and len(element2) >= 1:
            LOG.info("calling assert_array_of_hashes_equal()")
            self.assert_array_of_hashes_equal(element1, element2,
                                        primary_key=primary_key,
                                        keys_to_remove=keys_to_remove,
                                        msg=msg)
        else:
            self.fail("Wrong element items: %s&%s" % (len(element1), len(element2)))
