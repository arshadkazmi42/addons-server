# -*- coding: utf-8 -*-
import json

from django.conf import settings

from olympia import amo
from olympia.amo.tests import (
    APITestClient, ESTestCase, reverse_ns, create_switch)
from olympia.constants.search import SEARCH_LANGUAGE_TO_ANALYZER


class TestRankingScenarios(ESTestCase):
    client_class = APITestClient

    def _check_scenario(self, query, expected, no_match=None, **kwargs):
        def get_name_from_result(item, expected_lang):
            name = item['name'].get(expected_lang)
            if name is None:
                name = item['name'].get(item['default_locale'], '??????')
            return name

        # Use v4dev version to ensure we get objects for translations all the
        # time. We don't necessarily specify the language in all tests, but we
        # want objects all the time for simplicity.
        url = reverse_ns('addon-search', api_version='v4dev')
        params = {
            'lang': 'en-US'
        }
        expected_lang = kwargs.pop('expected_lang', None)
        params.update(kwargs)
        params['q'] = query
        response = self.client.get(url, params)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['count']
        results = data['results']

        if expected_lang is None:
            expected_lang = params['lang']
        # We only check for greater or equal since we usually don't care
        # about what else ElasticSearch finds magically for any query.
        # We're mostly concerned about the first few results to check
        # our general ranking. In real-world the rest that follows matches
        # the general scoring idea.
        assert len(results) >= len(expected), (
            'Expected {} results but {} found for query "{}": {}'.format(
                len(expected), len(results), query,
                [x['name'][expected_lang] for x in results]
            )
        )

        for idx, addon in enumerate(expected):
            expected_name = addon[0]
            expected_score = addon[1]
            found_name = get_name_from_result(results[idx], expected_lang)
            found_score = results[idx]['_score']

            assert found_name == expected_name, (
                'Expected "{}" to be on position {} with score {} but '
                '"{}" was found instead with score {} for query {}'
                .format(expected_name, idx, expected_score,
                        found_name, found_score, query)
            )

            # Quick and dirty way to generate a script to change the expected
            # scores in this file, uncomment this block then launch the script
            # it generates (note that it will skip the assert below because of
            # 'continue').
            # Don't forget to verify the diff afterwards to see if they make
            # sense though!)
            # if found_score != expected_score:
            #     filename = 'src/olympia/search/tests/test_search_ranking.py'
            #     with open('sed_me.sh', 'a+') as f:
            #         f.write('sed -i s/%s/%s/ %s\n' % (
            #             expected_score, found_score, filename))
            #     continue
            assert found_score == expected_score, (
                'Expected "{}" to be on position {} with score {} but '
                '"{}" was found instead with score {} for query {}'
                .format(expected_name, idx, expected_score,
                        found_name, found_score, query)
            )

        if no_match is not None:
            for name in no_match:
                names = [get_name_from_result(item, expected_lang)
                         for item in results]
                assert name not in names, (
                    'Expected "{}" not to exist in results for query {}'
                    .format(name, query)
                )

        return results

    @classmethod
    def setUpTestData(cls):
        # For simplicity reasons, let's simply use the new algorithm
        # we're most certainly going to put live anyway
        # Also, this needs to be created before `setUpTestData`
        # since we need that setting on index-creation time.
        create_switch('es-use-classic-similarity')

        super(TestRankingScenarios, cls).setUpTestData()

        # Shouldn't be necessary, but just in case.
        cls.empty_index('default')

        # This data was taken from our production add-ons to test
        # a few search scenarios. (2018-01-25)
        # Note that it's important to set average_daily_users for extensions
        # and weekly_downloads for themes (personas) in every case,  because it
        # affects the ranking score and otherwise addon_factory() sets a random
        # value.
        amo.tests.addon_factory(
            average_daily_users=18981,
            description=None,
            name='Tab Center Redux',
            slug=u'tab-center-redux',
            summary='Move your tabs to the side of your browser window.',
            weekly_downloads=915)
        amo.tests.addon_factory(
            average_daily_users=468126,
            description=None,
            name='Tab Mix Plus',
            slug=u'tab-mix-plus',
            summary=(
                'Tab Mix Plus enhances Firefox\'s tab browsing capabilities. '
                'It includes such features as duplicating tabs, controlling '
                'tab focus, tab clicking options, undo closed tabs and '
                'windows, plus much more. It also includes a full-featured '
                'session manager.'),
            weekly_downloads=3985)
        amo.tests.addon_factory(
            average_daily_users=8838,
            description=None,
            name='Redux DevTools',
            slug=u'remotedev',
            summary=(
                'DevTools for Redux with actions history, undo and replay.'),
            weekly_downloads=1032)
        amo.tests.addon_factory(
            average_daily_users=482,
            description=None,
            name='Open Image in New Tab',
            slug=u'open-image-new-tab',
            summary='Adds a context menu to open images in a new tab.',
            weekly_downloads=158)
        amo.tests.addon_factory(
            average_daily_users=2607,
            description=None,
            name='Open image in a new tab',
            slug=u'open-image-in-a-new-tab',
            summary='A context menu to open images in a new tab',
            weekly_downloads=329)
        amo.tests.addon_factory(
            average_daily_users=27832,
            description=None,
            name='Open Bookmarks in New Tab',
            slug=u'open-bookmarks-in-new-tab',
            summary=(
                'After you installed this addon to your Firefox, bookmarks '
                'are opened in new tab always.'),
            weekly_downloads=145)
        amo.tests.addon_factory(
            average_daily_users=528,
            description=None,
            name='Coinhive Blocker',
            slug=u'coinhive-blocker',
            summary='Coinhive mining blocker',
            weekly_downloads=132)
        amo.tests.addon_factory(
            average_daily_users=3015,
            description=None,
            name='CoinBlock',
            slug=u'coinblock',
            summary=(
                'With the rising popularity of coinminers in js form, this '
                'extension attempts to block those hosted on coin-hive, and '
                'cryptoloot.\nA multiple entry block list is planned.'),
            weekly_downloads=658)
        amo.tests.addon_factory(
            average_daily_users=418,
            description=None,
            name='NoMiners',
            slug=u'nominers',
            summary=(
                'NoMiners is an Add-on that tries to block cryptominers such '
                'as coinhive.\n\nBlocking those pesky miner scripts will '
                'relieve your CPU and BATTERY while browsing the web.'
                '\n\nIt\'s open source, so feel free to check out the code '
                'and submit improvements.'),
            weekly_downloads=71)
        amo.tests.addon_factory(
            average_daily_users=399485,
            description=None,
            name='Privacy Badger',
            slug=u'privacy-badger17',
            summary=(
                'Protects your privacy by blocking spying ads and invisible '
                'trackers.'),
            weekly_downloads=22931)
        amo.tests.addon_factory(
            average_daily_users=8728,
            description=None,
            name='Privacy Pass',
            slug=u'privacy-pass',
            summary=(
                'Handles passes containing cryptographically blinded tokens '
                'for bypassing challenge pages.'),
            weekly_downloads=4599)
        amo.tests.addon_factory(
            average_daily_users=15406,
            description=None,
            name='Privacy Settings',
            slug=u'privacy-settings',
            summary=(
                'Alter Firefox\'s built-in privacy settings easily with a '
                'toolbar panel.'),
            weekly_downloads=1492)
        amo.tests.addon_factory(
            average_daily_users=12857,
            description=None,
            name='Google Privacy',
            slug=u'google-privacy',
            summary=(
                'Make some popular websites respect your privacy settings.\n'
                'Please see the known issues below!'),
            weekly_downloads=117)
        amo.tests.addon_factory(
            average_daily_users=70553,
            description=None,
            name='Blur',
            slug=u'donottrackplus',
            summary='Protect your Passwords, Payments, and Privacy.',
            weekly_downloads=2224)
        amo.tests.addon_factory(
            average_daily_users=1009156,
            description=None,
            name='Ghostery',
            slug=u'ghostery',
            summary=(
                u'See who’s tracking you online and protect your privacy with '
                u'Ghostery.'),
            weekly_downloads=49315)
        amo.tests.addon_factory(
            average_daily_users=954288,
            description=None,
            name='Firebug',
            slug=u'firebug',
            summary=(
                'Firebug integrates with Firefox to put a wealth of '
                'development tools at your fingertips while you browse. You '
                'can edit, debug, and monitor CSS, HTML, and JavaScript live '
                'in any web page...'),
            weekly_downloads=21969)
        amo.tests.addon_factory(
            average_daily_users=10821,
            description=None,
            name='Firebug Autocompleter',
            slug=u'firebug-autocompleter',
            summary='Firebug command line autocomplete.',
            weekly_downloads=76)
        amo.tests.addon_factory(
            average_daily_users=11992,
            description=None,
            name='Firefinder for Firebug',
            slug=u'firefinder-for-firebug',
            summary=(
                'Finds HTML elements matching chosen CSS selector(s) or XPath '
                'expression'),
            weekly_downloads=358)
        amo.tests.addon_factory(
            average_daily_users=8200,
            description=None,
            name='Fire Drag',
            slug=u'fire-drag',
            summary='drag texts and links with/without e10s',
            weekly_downloads=506)
        amo.tests.addon_factory(
            average_daily_users=61014,
            description=None,
            name='Menu Wizard',
            slug=u's3menu-wizard',
            summary=(
                'Customizemenus=Helps removing, moving and renaming menus and '
                'menu items\nColorize important menu for ease of use! (use '
                'Style (CSS))\nChange or disable any of used keyboard '
                'shortcutsnSuppor=Firefox, Thunderbird and SeaMonkey'),
            weekly_downloads=927)
        amo.tests.addon_factory(
            average_daily_users=81237,
            description=None,
            name='Add-ons Manager Context Menu',
            slug=u'am-context',
            summary='Add more items to Add-ons Manager context menu.',
            weekly_downloads=169)
        amo.tests.addon_factory(
            average_daily_users=51,
            description=None,
            name='Frame Demolition',
            slug=u'frame-demolition',
            summary=(
                'Enabling route to load abstracted file layer in select '
                'sites.'),
            weekly_downloads=70)
        amo.tests.addon_factory(
            average_daily_users=99,
            description=None,
            name='reStyle',
            slug=u're-style',
            summary=(
                'A user style manager which can load local files and apply UI '
                'styles even in Firefox 57+'),
            weekly_downloads=70)
        amo.tests.addon_factory(
            average_daily_users=150,
            description=None,
            name='MegaUpload DownloadHelper',
            slug=u'megaupload-downloadhelper',
            summary=(
                'Download from MegaUpload.\nMegaUpload Download Helper will '
                'start your download once ready.\nMegaUpload Download Helper '
                'will monitor time limitations and will auto-start your '
                'download.'),
            weekly_downloads=77)
        amo.tests.addon_factory(
            average_daily_users=2830,
            description=None,
            name='RapidShare DownloadHelper',
            slug=u'rapidshare-downloadhelper',
            summary=(
                'Note from Mozilla: This add-on has been discontinued. Try '
                '<a rel="nofollow" href="https://addons.mozilla.org/firefox/'
                'addon/rapidshare-helper/">Rapidshare Helper</a> instead.\n\n'
                'RapidShare Download Helper will start your download once '
                'ready.'),
            weekly_downloads=125)
        amo.tests.addon_factory(
            average_daily_users=98716,
            description=None,
            name='Popup Blocker',
            slug=u'popup_blocker',
            summary=(
                'Prevents your web browser from opening a new window on top '
                'of the content or web site you are viewing. The Addon also '
                'supresses unwanted advertisement windows on your screen. '
                'The one deciding what consitutes a popup is the user.'),
            weekly_downloads=3940)
        amo.tests.addon_factory(
            average_daily_users=8830,
            description=None,
            name='No Flash',
            slug=u'no-flash',
            summary=(
                'Replace Youtube, Vimeo and Dailymotion Flash video players '
                'embedded on third-party website by the HTML5 counterpart '
                'when the content author still use the old style embed '
                '(Flash).\n\nSource code at <a rel="nofollow" href="https://'
                'outgoing.prod.mozaws.net/v1/14b404a3c05779fa94b24e0bffc0d710'
                '6836f1d6b771367b065fb96e9c8656b9/https%3A//github.com/hfigui'
                'ere/no-flash">https://github.com/hfiguiere/no-flash</a>'),
            weekly_downloads=77)
        amo.tests.addon_factory(
            average_daily_users=547880,
            description=None,
            name='Download Flash and Video',
            slug=u'download-flash-and-video',
            summary=(
                'Download Flash and Video is a great download helper tool '
                'that lets you download Flash games and Flash videos '
                '(YouTube, Facebook, Dailymotion, Google Videos and more) '
                'with a single click.\nThe downloader is very easy to use.'),
            weekly_downloads=65891)
        amo.tests.addon_factory(
            average_daily_users=158796,
            description=None,
            name='YouTube Flash Video Player',
            slug=u'youtube-flash-video-player',
            summary=(
                'YouTube Flash Video Player is a powerful tool that will let '
                'you choose Flash video player as default YouTube video '
                'player.'),
            weekly_downloads=12239)
        amo.tests.addon_factory(
            average_daily_users=206980,
            description=None,
            name='YouTube Flash Player',
            slug=u'youtube-flash-player',
            summary=(
                u'A very lightweight add-on that allows you to watch YouTube™ '
                u'videos using Flash® Player instead of the '
                u'default HTML5 player. The Flash® Player will consume less '
                u'CPU and RAM resources if your device doesn\'t easily '
                u'support HTML5 videos. Try it!'),
            weekly_downloads=21882)
        amo.tests.addon_factory(
            average_daily_users=5056, description=None,
            name='Disable Hello, Pocket & Reader+',
            slug=u'disable-hello-pocket-reader',
            summary=(
                'Turn off Pocket, Reader, Hello and WebRTC bloatware - keep '
                'browser fast and clean'),
            weekly_downloads=85)
        amo.tests.addon_factory(
            average_daily_users=26135,
            description=None,
            name='Reader',
            slug=u'reader',
            summary='Reader is the ultimate Reader tool for Firefox.',
            weekly_downloads=2463)
        amo.tests.addon_factory(
            average_daily_users=53412,
            description=None,
            name='Disable WebRTC',
            slug=u'happy-bonobo-disable-webrtc',
            summary=(
                'WebRTC leaks your actual IP addresses from behind your VPN, '
                'by default.'),
            weekly_downloads=10583)
        amo.tests.addon_factory(
            average_daily_users=12953,
            description=None,
            name='In My Pocket',
            slug=u'in-my-pocket',
            summary=(
                'For all those who are missing the old Firefox Pocket addon, '
                'and not satisfied with the new Pocket integration, here is '
                'an unofficial client for the excellent Pocket service. '
                'Hope you\'ll enjoy it!'),
            weekly_downloads=1123)
        amo.tests.addon_factory(
            name='GrApple Yummy', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1)
        amo.tests.addon_factory(
            name='Delicious Bookmarks', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1)

        # Some more or less Dummy data to test a few very specific scenarios
        # e.g for exact name matching
        amo.tests.addon_factory(
            name='Merge Windows', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1),
        amo.tests.addon_factory(
            name='Merge All Windows', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1),
        amo.tests.addon_factory(
            name='All Downloader Professional', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1),

        amo.tests.addon_factory(
            name='test addon test11', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1),
        amo.tests.addon_factory(
            name='test addon test21', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1),
        amo.tests.addon_factory(
            name='test addon test31', type=amo.ADDON_EXTENSION,
            average_daily_users=1, weekly_downloads=1),

        names = {
            'fr': 'Foobar unique francais',
            'en-US': 'Foobar unique english',
        }
        amo.tests.addon_factory(
            name=names, type=amo.ADDON_EXTENSION,
            default_locale='fr', slug='test-addon-test-special',
            average_daily_users=1, weekly_downloads=1)

        amo.tests.addon_factory(
            name='1-Click YouTube Video Download',
            type=amo.ADDON_EXTENSION,
            average_daily_users=566337, weekly_downloads=150000,
            description=(
                'button, click that button, 1-Click Youtube Video '
                'Downloader is a click click great tool')),
        amo.tests.addon_factory(
            name='Amazon 1-Click Lock', type=amo.ADDON_EXTENSION,
            average_daily_users=50, weekly_downloads=1),

        cls.refresh()

    def test_scenario_tab_center_redux(self):
        self._check_scenario('tab center redux', (
            ['Tab Center Redux', 69.21394],
            ['Tab Mix Plus', 0.06495905],
            ['Redux DevTools', 0.04430029],
        ))

    def test_scenario_open_image_new_tab(self):
        self._check_scenario('Open Image in New Tab', (
            ['Open Image in New Tab', 24.277237],
            ['Open image in a new tab', 5.6800475],
        ))

    def test_scenario_coinhive(self):
        # TODO, should match "CoinBlock". Check word delimiting analysis maybe?
        self._check_scenario('CoinHive', (
            ['Coinhive Blocker', 3.891288],
            ['NoMiners', 0.017959397],  # via description
            # ['CoinBlock', 0],  # via prefix search
        ))

    def test_scenario_privacy(self):
        self._check_scenario('Privacy', (
            ['Privacy Badger', 8.7432165],
            ['Privacy Settings', 4.559415],
            ['Google Privacy', 4.350088],  # More users, summary
            ['Privacy Pass', 3.2087922],
            ['Ghostery', 0.09441561],  # Crazy amount of users, summary
            # summary + a lot of users, but not as many as ghostery
            ['Blur', 0.0776396],
        ))

    def test_scenario_firebu(self):
        self._check_scenario('firebu', (
            ['Firebug', 4.117813],
            ['Firefinder for Firebug', 1.0876373],
            ['Firebug Autocompleter', 1.0655142],
            ['Fire Drag', 0.6470381],
        ))

    def test_scenario_fireb(self):
        self._check_scenario('fireb', (
            ['Firebug', 4.117813],
            ['Firefinder for Firebug', 1.0876373],
            ['Firebug Autocompleter', 1.0655142],
            ['Fire Drag', 0.6470381],
        ))

    def test_scenario_menu_wizzard(self):
        self._check_scenario('Menu Wizzard', (
            ['Menu Wizard', 0.10683497],  # (fuzzy, typo)
            # partial match + users
            ['Add-ons Manager Context Menu', 0.0791911],
        ))

    def test_scenario_frame_demolition(self):
        self._check_scenario('Frame Demolition', (
            ['Frame Demolition', 20.48827],
        ))

    def test_scenario_demolition(self):
        # Find "Frame Demolition" via a typo
        self._check_scenario('Demolation', (
            ['Frame Demolition', 0.057878494],
        ))

    def test_scenario_restyle(self):
        self._check_scenario('reStyle', (
            ['reStyle', 26.352535],
        ))

    def test_scenario_megaupload_downloadhelper(self):
        # Doesn't find "RapidShare DownloadHelper" anymore
        # since we now query by "MegaUpload AND DownloadHelper"
        self._check_scenario('MegaUpload DownloadHelper', (
            ['MegaUpload DownloadHelper', 42.920856],
        ))

    def test_scenario_downloadhelper(self):
        # No direct match, "Download Flash and Video" has
        # huge amount of users that puts it first here
        self._check_scenario('DownloadHelper', (
            ['RapidShare DownloadHelper', 3.1008768],
            ['MegaUpload DownloadHelper', 1.7232388],
            ['Download Flash and Video', 1.5117542],
            ['1-Click YouTube Video Download', 1.141354],
        ))

    def test_scenario_megaupload(self):
        self._check_scenario('MegaUpload', (
            ['MegaUpload DownloadHelper', 3.269901],
            ['Popup Blocker', 1.4292603],
        ))

    def test_scenario_no_flash(self):
        self._check_scenario('No Flash', (
            ['No Flash', 46.64575],
            ['Download Flash and Video', 4.4118795],
            ['YouTube Flash Player', 3.5120416],
            ['YouTube Flash Video Player', 3.202704],
        ))

        # Case should not matter.
        self._check_scenario('no flash', (
            ['No Flash', 46.64575],
            ['Download Flash and Video', 4.4118795],
            ['YouTube Flash Player', 3.5120416],
            ['YouTube Flash Video Player', 3.202704],
        ))

    def test_scenario_disable_hello_pocket_reader_plus(self):
        self._check_scenario('Disable Hello, Pocket & Reader+', (
            ['Disable Hello, Pocket & Reader+', 59.37624],  # yeay!
        ))

    def test_scenario_grapple(self):
        """Making sure this scenario works via the API,

        see `legacy_api.SearchTest` for various examples.
        """
        self._check_scenario('grapple', (
            ['GrApple Yummy', 0.97180986],
        ))

    def test_scenario_delicious(self):
        """Making sure this scenario works via the API,

        see `legacy_api.SearchTest` for various examples.
        """
        self._check_scenario('delicious', (
            ['Delicious Bookmarks', 1.1302524],
        ))

    def test_score_boost_name_match(self):
        # Tests that we match directly "Merge Windows" and also find
        # "Merge All Windows" because of slop=1
        self._check_scenario('merge windows', (
            ['Merge Windows', 12.554659],
            ['Merge All Windows', 1.7936656],
        ), no_match=(
            'All Downloader Professional',
        ))

        self._check_scenario('merge all windows', (
            ['Merge All Windows', 14.103567],
            ['Merge Windows', 0.042702418],
            ['All Downloader Professional', 0.0070751677],
        ))

    def test_score_boost_exact_match(self):
        """Test that we rank exact matches at the top."""
        self._check_scenario('test addon test21', (
            ['test addon test21', 14.293872],
        ))

    def test_score_boost_exact_match_description_hijack(self):
        """Test that we rank exact matches at the top."""
        self._check_scenario('Amazon 1-Click Lock', (
            ['Amazon 1-Click Lock', 34.255657],
            ['1-Click YouTube Video Download', 0.22216046],
        ))

    def test_score_boost_exact_match_in_right_language(self):
        """Test that exact matches are using the translation if possible."""
        # First in english. Straightforward: it should be an exact match, the
        # translation exists.
        self._check_scenario(u'foobar unique english', (
            [u'Foobar unique english', 4.675893],
        ), lang='en-US')

        # Then check in french. Also straightforward: it should be an exact
        # match, the translation exists, it's even the default locale.
        self._check_scenario(u'foobar unique francais', (
            [u'Foobar unique francais', 14.146512],
        ), lang='fr')

        # Check with a language that we don't have a translation for (mn), and
        # that we do not have a language-specific analyzer for. Note that we
        # need to pass expected_lang because the name object won't contain
        # 'mn', instead it will return an object with the default_locale for
        # this addon.
        assert 'mn' not in SEARCH_LANGUAGE_TO_ANALYZER
        assert 'mn' in settings.LANGUAGES
        self._check_scenario(u'foobar unique francais', (
            [u'Foobar unique francais', 12.54679],
        ), lang='mn', expected_lang='fr')

        # Check with a language that we don't have a translation for (ca), and
        # that we *do* have a language-specific analyzer for. Note that we need
        # to pass expected_lang because the name object won't contain 'ca',
        # instead it will return an object with the default_locale for this
        # addon.
        assert 'ca' in SEARCH_LANGUAGE_TO_ANALYZER
        assert 'ca' in settings.LANGUAGES
        self._check_scenario(u'foobar unique francais', (
            [u'Foobar unique francais', 11.289922],
        ), lang='ca', expected_lang='fr')

        # Check with a language that we do have a translation for (en-US), but
        # we're requesting the string that matches the default locale (fr).
        # Note that the name returned follows the language requested.
        self._check_scenario(u'foobar unique francais', (
            [u'Foobar unique english', 9.786429],
        ), lang='en-US')
