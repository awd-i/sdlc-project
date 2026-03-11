/* SPDX-License-Identifier: MIT
 *
 * Copyright (C) 2017-2025 WireGuard LLC. All Rights Reserved.
 */

package ratelimiter

import (
	"net/netip"
	"testing"
	"time"
)

// TestRatelimiterBurstCount verifies that the initial burst from a
// previously-unseen IP is exactly packetsBurstable packets -- no more,
// no less.  A common off-by-one is to initialise the token bucket at
// maxTokens instead of maxTokens-packetCost, which grants one extra
// packet because the very first Allow() call returns true without
// deducting from the bucket.
func TestRatelimiterBurstCount(t *testing.T) {
	var rate Ratelimiter

	now := time.Now()
	rate.timeNow = func() time.Time { return now }
	rate.Init()
	defer rate.Close()
	defer func() {
		rate.mu.Lock()
		defer rate.mu.Unlock()
		rate.timeNow = time.Now
	}()

	ip := netip.MustParseAddr("10.0.0.1")

	allowed := 0
	for i := 0; i < packetsBurstable+5; i++ {
		if rate.Allow(ip) {
			allowed++
		}
	}

	if allowed != packetsBurstable {
		t.Fatalf("initial burst allowed %d packets, want exactly %d (packetsBurstable)", allowed, packetsBurstable)
	}
}

// TestRatelimiterBurstMultipleIPs confirms the burst limit is enforced
// independently for every source IP and that none of them overshoot.
func TestRatelimiterBurstMultipleIPs(t *testing.T) {
	var rate Ratelimiter

	now := time.Now()
	rate.timeNow = func() time.Time { return now }
	rate.Init()
	defer rate.Close()
	defer func() {
		rate.mu.Lock()
		defer rate.mu.Unlock()
		rate.timeNow = time.Now
	}()

	ips := []netip.Addr{
		netip.MustParseAddr("192.168.1.1"),
		netip.MustParseAddr("10.10.10.10"),
		netip.MustParseAddr("172.16.0.1"),
		netip.MustParseAddr("2001:db8::1"),
		netip.MustParseAddr("fd00::abcd"),
	}

	for _, ip := range ips {
		allowed := 0
		for i := 0; i < packetsBurstable+5; i++ {
			if rate.Allow(ip) {
				allowed++
			}
		}
		if allowed != packetsBurstable {
			t.Errorf("IP %s: initial burst allowed %d packets, want %d", ip, allowed, packetsBurstable)
		}
	}
}

// TestRatelimiterTokenRecovery checks that after the burst is exhausted
// and exactly one packet-interval elapses, exactly one more packet is
// allowed (no residual extra token from initialisation).
func TestRatelimiterTokenRecovery(t *testing.T) {
	var rate Ratelimiter

	now := time.Now()
	rate.timeNow = func() time.Time { return now }
	rate.Init()
	defer rate.Close()
	defer func() {
		rate.mu.Lock()
		defer rate.mu.Unlock()
		rate.timeNow = time.Now
	}()

	ip := netip.MustParseAddr("10.0.0.99")

	// Drain the initial burst.
	for i := 0; i < packetsBurstable+3; i++ {
		rate.Allow(ip)
	}

	// Advance time by exactly one packet interval.
	now = now.Add(time.Second/packetsPerSecond + 1)
	rate.cleanup()

	if !rate.Allow(ip) {
		t.Fatal("expected one packet to be allowed after waiting one interval")
	}
	if rate.Allow(ip) {
		t.Fatal("expected second packet to be rejected after single-interval refill")
	}
}
