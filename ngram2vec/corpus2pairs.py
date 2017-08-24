from math import sqrt
from random import Random
from docopt import docopt
import multiprocessing
from corpus2vocab import getNgram
from representations.matrix_serializer import load_count_vocabulary


def main():
    args = docopt("""
    Usage:
        corpus2pairs.py [options] <corpus> <vocab> <pairs>

    Options:
        --win NUM                  Window size [default: 2]
        --sub NUM                  Subsampling threshold [default: 0]
        --ngram_word NUM           (Center) word vocabulary includes grams of 1st to nth order [default: 1]
        --ngram_context NUM        Context vocabulary includes grams of 1st to nth order [default: 1]
        --threads_num NUM          The number of threads [default: 8]
        --overlap                  Whether overlaping pairs are allowed or not
    """)

    print "**********************"
    print "corpus2pairs"
    threads_num = int(args['--threads_num'])
    threads_list = []
    for i in xrange(0, threads_num): #extract pairs from corpus through multipule threads
        thread = multiprocessing.Process(target=c2p, args=(args, i))
        thread.start()
        threads_list.append(thread)
    for thread in threads_list:
        thread.join()
    print "corpus2pairs finished"


def c2p(args, tid):
    pairs_file = open(args['<pairs>']+"_"+str(tid), 'w')
    win = int(args['--win'])
    subsample = float(args['--sub'])
    sub = subsample != 0
    ngram_word = int(args['--ngram_word'])
    ngram_context = int(args['--ngram_context'])
    overlap = args['--overlap']
    threads_num = int(args['--threads_num'])

    vocab = load_count_vocabulary(args['<vocab>']) #load vocabulary (generated in corpus2vocab stage)
    train_uni_num = 0 #number of (unigram) tokens in corpus
    for w, c in vocab.iteritems():
        if '@$' not in w:
            train_uni_num += c
    train_num = sum(vocab.values()) #number of (ngram) tokens in corpus
    if tid == 0:
        print 'vocabulary size: ' + str(len(vocab))
        print 'number of training words (uni-grams): ' + str(train_uni_num)    
        print 'number of training n-grams: ' + str(train_num)
    subsample *= train_uni_num
    if sub:
        subsampler = dict([(word, 1 - sqrt(subsample / count)) for word, count in vocab.iteritems() if count > subsample]) #subsampling technique

    rnd = Random(17)
    with open(args['<corpus>']) as f:
        line_num = 0
        if tid == 0:
            print str(line_num/1000**1) + "K lines processed."
        for line in f:
            line_num += 1
            if ((line_num) % 1000) == 0 and tid == 0:
                print "\x1b[1A" + str(line_num/1000) + "K lines processed."
            if line_num % threads_num != tid:
                continue
            tokens = line.strip().split()
            for i in xrange(len(tokens)): #loop for each position in a line
                for gram_word in xrange(1, ngram_word+1): #loop for grams of different orders in (center) word 
                    word = getNgram(tokens, i, gram_word)
                    word = check_word(word, vocab, sub, subsampler, rnd)
                    if word is None:
                        continue
                    for gram_context in xrange(1, ngram_context+1): #loop for grams of different orders in context
                        start = i - win + gram_word - 1
                        end = i + win - gram_context + 1
                        for j in xrange(start, end + 1):
                            if overlap:
                                if i == j and gram_word == gram_context:
                                    continue
                            else:
                                if len(set(range(i, i + gram_word)) & set(range(j, j + gram_context))) > 0:
                                    continue
                            context = getNgram(tokens, j, gram_context)
                            context = check_word(context, vocab, sub, subsampler, rnd)
                            if context is None:
                                continue
                            pairs_file.write(word + ' ' + context + "\n") #write pairs to the file
    pairs_file.close()
                        

def check_word(t, vocab, sub, subsampler, rnd): #discard tokens
    if t is None:
        return None
    if sub:
        t = t if t not in subsampler or rnd.random() > subsampler[t] else None
        if t is None:
            return None
    t = t if t in vocab else None
    return t


if __name__ == '__main__':
    main()

