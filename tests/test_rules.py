from datetime import datetime, timedelta, timezone
from math import hypot

import pytest
from sitecare.rules import (assess_point, body_to_image, default_sites, image_to_body,
                           iso, nearest_site, parse_time, photo_ready, screen_sites)

NOW = datetime(2026, 9, 12, 3, 0, tzinfo=timezone.utc)
P = {'x': 0, 'y': -6}


def photo(**values):
    d = {'verified': 1, 'width': 1200, 'height': 1000, 'captured_at': iso(NOW),
         'alignment': {'cx': 600, 'cy': 520, 'angle': 0, 'ppm': 30,
                       'calibration': {'length_cm': 10}}}
    d.update(values)
    return d


def event(ago=0, n=1, x=0, y=-6, **values):
    return {'id': 1, 'site_number': n, 'x': x, 'y': y, 'voided_at': None,
            'occurred_at': iso(NOW-timedelta(days=ago)), **values}


def alert(ago=0, **values):
    return {'id': 1, 'site_number': 1, 'x': 0, 'y': -6, 'radius': 1,
            'observed_at': iso(NOW-timedelta(days=ago)), 'resolved_at': None,
            'types': ['redness'], **values}


def assess(events=None, alerts=None, point=None, reviews=None, **kwargs):
    return assess_point(point or P, 1, events or [], alerts or [], reviews or [], photo(), NOW, **kwargs)


def test_default_layout_has_14_unique_correct_numbers():
    s = default_sites()
    assert [v['number'] for v in s] == list(range(1, 15))
    assert s[0]['x'] == 0 and s[0]['y'] == -6
    assert s[2]['x'] == 6 and s[4]['y'] == 6
    assert s[8]['x'] > 0 and s[11]['x'] < 0


def test_default_layout_geometric_minima():
    s = default_sites()
    assert all(hypot(a['x'], a['y']) >= 5 for a in s)
    assert all(hypot(a['x']-b['x'], a['y']-b['y']) >= 2.5
               for i, a in enumerate(s) for b in s[i+1:])


@pytest.mark.parametrize('angle', [-170, -45, 0, 30, 179])
def test_rotation_and_scale_round_trip(angle):
    a = {'cx': 507, 'cy': 304, 'ppm': 39.3, 'angle': angle}
    q = body_to_image(-3.7, 8.3, a)
    x, y = image_to_body(*q, a)
    assert x == pytest.approx(-3.7)
    assert y == pytest.approx(8.3)


def test_no_history_candidates_three_in_number_order():
    states, candidates = screen_sites(default_sites(), [], [], [], photo(), NOW)
    assert len(states) == 14
    assert candidates == [1, 2, 3]


def test_recovered_site_returns_to_rotation_despite_history():
    sites = default_sites()
    last = event(ago=1, n=2, x=sites[1]['x'], y=sites[1]['y'])
    concern = alert(ago=1, site_number=5, x=0, y=6)
    assert screen_sites(sites, [last], [concern], [], photo(), NOW)[1] == [3, 4, 6]
    concern['resolved_at'] = iso(NOW)
    old_use = event(ago=20, n=5, x=0, y=6, id=2)
    assert screen_sites(sites, [last, old_use], [concern], [], photo(), NOW)[1] == [3, 4, 5]


def test_rotation_wraps_after_site_14():
    sites = default_sites()
    last = event(n=14, x=sites[13]['x'], y=sites[13]['y'])
    assert screen_sites(sites, [last], [], [], photo(), NOW)[1] == [1, 2, 3]


def test_void_only_applies_from_its_recorded_time():
    e = event(ago=1, voided_at=iso(NOW + timedelta(days=1)))
    assert assess(events=[e])['status'] == 'resting'


def test_same_number_locked_even_when_exact_points_far_apart():
    result = assess(events=[event(ago=1, x=0, y=-15)])
    assert result['status'] == 'resting'
    assert result['rest_seconds'] == 11 * 86400


def test_nearby_different_number_also_locks():
    result = assess(events=[event(ago=1, n=2, x=1, y=-6)])
    assert result['status'] == 'resting'
    assert result['reasons'][0]['code'] == 'near_recent'


def test_exact_2point5_distance_allowed_for_other_number():
    assert assess(events=[event(ago=1, n=2, x=2.5, y=-6)])['status'] == 'eligible'


def test_one_second_before_12_days_still_locked():
    e = event(occurred_at=iso(NOW-timedelta(days=12)+timedelta(seconds=1)))
    assert assess(events=[e])['rest_seconds'] == 1


def test_exact_12_days_unlocks():
    assert assess(events=[event(ago=12)])['status'] == 'eligible'


def test_latest_of_multiple_nearby_locks_controls_countdown():
    r = assess(events=[event(ago=11), event(ago=2, n=2, x=1, id=2)])
    assert r['rest_seconds'] == 10 * 86400


def test_voided_events_do_not_block():
    assert assess(events=[event(voided_at=iso(NOW))])['status'] == 'eligible'


def test_future_events_do_not_apply_to_past_assessment():
    assert assess(events=[event(ago=-1)])['status'] == 'eligible'


def test_active_skin_alert_does_not_expire_after_many_days():
    r = assess(alerts=[alert(ago=200)])
    assert r['status'] == 'blocked'
    assert any(v['code'] == 'active_alert' for v in r['reasons'])


def test_red_skin_alert_has_priority_over_blue_rest():
    r = assess(events=[event(ago=1)], alerts=[alert()])
    assert r['status'] == 'blocked'
    assert r['rest_seconds'] == 11 * 86400


def test_resolved_single_alert_clears_only_skin_restriction():
    a = alert(ago=2, resolved_at=iso(NOW-timedelta(days=1)))
    assert assess(alerts=[a])['status'] == 'eligible'
    assert assess(events=[event(ago=2)], alerts=[a])['status'] == 'resting'


def test_resolved_recurrence_unblocks_without_review():
    aa = [alert(ago=30, resolved_at=iso(NOW-timedelta(days=29))),
          alert(ago=4, id=2, resolved_at=iso(NOW-timedelta(days=3)))]
    assert assess(alerts=aa)['status'] == 'eligible'
    assert not assess(alerts=aa)['needs_review']
    review = [{'site_number': 1, 'through_alert_id': 2}]
    assert assess(alerts=aa, reviews=review)['status'] == 'eligible'
    aa.append(alert(ago=2, id=3, resolved_at=iso(NOW-timedelta(days=1))))
    assert assess(alerts=aa, reviews=review)['status'] == 'eligible'
    assert not assess(alerts=aa, reviews=review)['needs_review']


def test_review_never_clears_an_active_area():
    aa = [alert(ago=2), alert(ago=1, id=2)]
    assert assess(alerts=aa, reviews=[{'site_number': 1, 'through_alert_id': 2}])['status'] == 'blocked'


def test_inside_navel_radius_blocked_at_exact_boundary_allowed():
    assert assess(point={'x': 0, 'y': -4.999})['status'] == 'blocked'
    assert assess(point={'x': 0, 'y': -5})['status'] == 'eligible'


def test_photo_missing_unverified_or_stale_never_green():
    for p in (None, photo(verified=0), photo(captured_at=iso(NOW-timedelta(hours=25)))):
        states, candidates = screen_sites(default_sites(), [], [], [], p, NOW)
        assert not candidates
        assert all(s['status'] != 'eligible' for s in states)


def test_future_photo_is_not_ready():
    assert not photo_ready(photo(captured_at=iso(NOW+timedelta(seconds=1))), NOW)


def test_point_outside_photo_blocked():
    assert assess(point={'x': 30, 'y': 0})['status'] == 'blocked'


def test_nearest_site_uses_point_not_claimed_number():
    assert nearest_site({'x': 5.9, 'y': .1}, default_sites()) == 3


def test_fewer_than_three_candidates_not_filled_with_blocked_sites():
    sites = default_sites()
    ee = [event(ago=1, n=s['number'], x=s['x'], y=s['y'], id=s['number']) for s in sites[:13]]
    _, candidates = screen_sites(sites, ee, [], [], photo(), NOW)
    assert candidates == [14]


def test_timezone_requires_offset_and_normalizes_jst():
    assert parse_time('2026-09-12T12:00:00+09:00') == NOW
    with pytest.raises(ValueError):
        parse_time('2026-09-12T12:00:00')
