#! /usr/bin/python

import itertools
import threading
import requests
import Queue
import time
import sys

#Provide a list of currencies we care about
CURRENCIES = [
        "USD", #U.S. Dollar
        "EUR", #Euro Dollar
        "JPY", #Japanese Yen
        "SGD", #Singapore Dollar
        "CHF", #Swiss Franc
        "HKD", #Hong Kong Dollar
        #"CNY",
        #"AED",
        #"SAR",
        #"TWD",
        #"SEK",
        #"INR",
        #"THB",
        #"MYR",
        ]

PAIRS = (itertools.permutations(CURRENCIES,2))
FX_PAIRS = {}
queue = Queue.Queue()

#We have lots of crap to grab, so let's create threading pool
class ThreadUrl(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        """
        Called by get_currency_pairs.
        """
        #core logic behind the grabbing of fx rates
        headers = {
            'User-Agent': 'Mozilla/5.0',
        }
        while True:
            pair = self.queue.get()
            url = "http://rate-exchange.appspot.com/currency?from=" + pair[0] + "&to=" + pair[1] + "&q=1"
            r = requests.get(url, headers=headers)
            exec('rate = ' + r.content) #We're going to be naive and pretend the incoming API data is safe...
            print "Rate: %s" % rate
            name = "%s_%s" % (pair[0], pair[1])
            FX_PAIRS[name] = rate['rate']
            self.queue.task_done()

def get_currency_pairs():
    """
    Gets all the currency pairs from the global PAIRS, spawns a pool of threads,
    and joins the threads when they're done. The actual grabbing of the pairs is
    called in the ThreadUrl class.
    """
    #spawn a pool of threads
    for i in range(5):
        t = ThreadUrl(queue)
        t.setDaemon(True)
        t.start()
        #populate the queue with data
        for pair in PAIRS:
            queue.put(pair)
    queue.join()

def arbitrage(amount_init, paths, min_profit=0.01):
    """
    Given an intial amount and a list containing tuples of possible arbitrage
    paths, returns paths that generate a profit.

    Optional argument 'min_profit' allows one to take into account transaction
    costs, etc.
    """
    print "Looking through all possible paths for a profit above %s " % (min_profit)
    arbitrage_opportunities = list()
    for path in paths:
        amount = amount_init
        pairs = (path[i] + "_" + path[i+1] for i in range(0,len(path)-1))
        for pair in pairs:
            amount = float(amount) * float(FX_PAIRS[pair])
        profit = amount - amount_init
        if profit > min_profit:
            arbitrage_opportunities.append(path + (profit,))
    return arbitrage_opportunities

def get_paths(rng, base_currency='USD'):
    """
    Takes the FX_PAIRS values and returns a list of all possible arbitrage
    paths.  This will almost certainly be passed on to the arbitrage function
    above. If provided a base currency that isn't in the data, exits gracefully.

    Option argument 'base_currency' allows one to specify a base currency other
    than USD.
    """
    print "Calculating paths...."
    currencies = list()
    currencies += (currency[:3] for currency in FX_PAIRS.keys() if currency[:3] not
            in currencies)
    if not base_currency in currencies:
        print "Unlisted currency: '%s'." % base_currency
        sys.exit(0)
    possible_paths = list()
    possible_paths += (path + (base_currency,) for path in itertools.permutations(currencies, rng) if path[0] == base_currency)
    print "%s possible paths...." % len(possible_paths)
    return possible_paths

def make_path_tuple_pretty(path):
    """
    Takes a currency path tuple, which are not particularly pleasing to look at,
    and makes it look pretty.
    """
    pretty_path = '['
    for i in range(0, len(path)-1):
        pretty_path += "%s -> " % path[i]
    pretty_path += path[-1] + ']'
    return pretty_path

def main():
    start_time = time.time()
    #if you provide a currency amount when you call the program use it,
    #otherwise ask for it.
    if len(sys.argv) > 1:
        init = sys.argv[1]
    else:
        init = raw_input("\nEnter initial amount: $")

    #if a currency is provided, use that as the base, otherwise default to USD
    #'cause....murica.
    if len(sys.argv) > 2:
        base_currency = sys.argv[2]    
    else:
        base_currency = 'USD'

    #Get the currency pairs, they are assigned to the FX_PAIRS global var
    get_currency_pairs()

    #check to see if any arbitrage opportunities exist and report what they are
    a = list()
    for r in range(2, len(CURRENCIES)):
        try:
            a += arbitrage(float(init), get_paths(r, base_currency))
        except MemoryError as e:
            print "Ran out of memory on %s-length path, use fewer currencies or buy more memory." % r
            break
    end_time = time.time()
    run_time = end_time - start_time
    print "Total run-time: %.2fs" % run_time
    if len(a) >0 :
        print "\nArbitrage opportunities exist and generate the following profit off a %s %s initial investment.\n" % (base_currency, init)
        max_profit = max(pair[-1] for pair in a if pair[-1] > 0) 
        good_deal = filter(lambda x: x[-1] == max_profit, a)[0]
        print "MAX PROFIT! Path %s generates %s %.2f in profit." % (make_path_tuple_pretty(good_deal[:-1]), base_currency, max_profit)

    else:
        print "You are fighting an army of robots, they are winning because forex arbitrage is a fools game."

if __name__=="__main__":
    main()

